#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du protocole de téléchargement par f4m

#
# Modules
#

import base64
import binascii
import hashlib
import hmac
import os
import StringIO
import struct
import urllib
import urllib2
import xml.etree.ElementTree
import zlib

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from Downloader    import Downloader, DownloaderException

import logging
logger = logging.getLogger("pluzzdl")

class DlF4m(Downloader):
    """
    Téléchargement des liens f4m
    """

    adobePlayer = "http://fpdownload.adobe.com/strobe/FlashMediaPlayback_101.swf"

    def __init__(self,
                 manifestUrl,
                 manifestUrlToken,
                 nomFichier,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.manifestUrl = manifestUrl
        self.manifestUrlToken = manifestUrlToken
        self.nomFichier = nomFichier
        self.navigateur = navigateur
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct

        self.historique = Historique()
        self.configuration = Configuration()
        self.hmacKey = self.configuration["hmac_key"].decode("hex")
        self.playerHash = self.configuration["player_hash"]

    def parseManifest(self):
        """
        Parse le manifest
        """
        try:
            arbre = xml.etree.ElementTree.fromstring(self.manifest)
            # Duree
            self.duree = float(arbre.find(
                    "{http://ns.adobe.com/f4m/1.0}duration").text)
            self.pv2 = arbre.find("{http://ns.adobe.com/f4m/1.0}pv-2.0").text
            media = arbre.findall("{http://ns.adobe.com/f4m/1.0}media")[-1]
            # Bitrate
            self.bitrate = int(media.attrib["bitrate"])
            # URL des fragments
            urlbootstrap = media.attrib["url"]
            self.urlFrag = "%s%sSeg1-Frag" % (
                self.manifestUrlToken[: self.manifestUrlToken.find(
                        "manifest.f4m")],
                urlbootstrap)
            # Header du fichier final
            self.flvHeader = base64.b64decode(
                media.find("{http://ns.adobe.com/f4m/1.0}metadata").text)
        except:
            raise DownloaderException("Impossible de parser le manifest")

    def ouvrirNouvelleVideo(self):
        """
        Créer une nouvelle vidéo
        """
        try:
            # Ouverture du fichier
            self.fichierVideo = open(self.nomFichier, "wb")
        except:
            raise DownloaderException(
                "Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
        # Ajout de l'en-tête FLV
        self.fichierVideo.write(binascii.a2b_hex(
                "464c56010500000009000000001200010c00000000000000"))
        # Ajout du header du fichier
        self.fichierVideo.write(self.flvHeader)
        # Padding pour avoir des blocs de 8
        self.fichierVideo.write(binascii.a2b_hex("00000000"))

    def decompressSWF(self, swfData):
        """
        Décompresse un fichier swf
        """
        # Adapted from:
        #    Prozacgod
        #    http://www.python-forum.org/pythonforum/viewtopic.php?f=2&t=14693
        if(type(swfData) is str):
            swfData = StringIO.StringIO(swfData)

        swfData.seek(0, 0)
        magic = swfData.read(3)

        if(magic == "CWS"):
            return "FWS" + swfData.read(5) + zlib.decompress(swfData.read())
        else:
            return None

    def getPlayerHash(self):
        """
        Récupère le sha256 du player flash
        """
        # Get SWF player
        playerData = self.navigateur.getFichier("http://static.francetv.fr/players/Flash.H264/player.swf")
        # Uncompress SWF player
        playerDataUncompress = self.decompressSWF(playerData)
        # Perform sha256 of uncompressed SWF player
        hashPlayer = hashlib.sha256(playerDataUncompress).hexdigest()
        # Perform base64
        return base64.encodestring(hashPlayer.decode('hex'))

    def debutVideo(self, fragID, fragData):
        """
        Trouve le début de la vidéo dans un fragment
        """
        # Skip fragment header
        start = fragData.find("mdat") + 4
        # For all fragment (except frag1)
        if(fragID > 1):
            # Skip 2 FLV tags
            for dummy in range(2):
                tagLen, = struct.unpack_from(">L", fragData, start)  # Read 32 bits (big endian)
                tagLen &= 0x00ffffff  # Take the last 24 bits
                start += tagLen + 11 + 4  # 11 = tag header len ; 4 = tag footer len
        return start

    def telecharger(self):
        # Récupère le manifest
        self.manifest = self.navigateur.getFichier(self.manifestUrlToken)
        # Parse le manifest
        self.parseManifest()
        # Calcul les elements
        self.hdnea = self.manifestUrlToken[self.manifestUrlToken.find("hdnea"):]
        self.pv20, self.hdntl = self.pv2.split(";")
        self.pvtokenData = r"st=0000000000~exp=9999999999~acl=%2f%2a~data=" + self.pv20 + "!" + self.playerHash
        self.pvtoken = "pvtoken=%s~hmac=%s" % (
            urllib.quote(self.pvtokenData),
            hmac.new(self.hmacKey,
                     self.pvtokenData,
                     hashlib.sha256).hexdigest())

        #
        # Création de la vidéo
        #
        self.premierFragment = 1
        self.telechargementFini = False

        video = self.historique.getVideo(self.urlFrag)
        # Si la vidéo est dans l'historique
        if(video is not None):
            # Si la video existe sur le disque
            if(os.path.exists(self.nomFichier)):
                if(video.finie):
                    logger.info("La vidéo a déjà été entièrement téléchargée")
                    return
                else:
                    self.ouvrirVideoExistante()
                    self.premierFragment = video.fragments
                    logger.info("Reprise du téléchargement de la vidéo au fragment %d" % (video.fragments))
            else:
                self.ouvrirNouvelleVideo()
                logger.info("Impossible de reprendre le téléchargement de la vidéo, le fichier %s n'existe pas" % (self.nomFichier))
        else:  # Si la vidéo n'est pas dans l'historique
            self.ouvrirNouvelleVideo()

        # Calcul l'estimation du nombre de fragments
        self.nbFragMax = round(self.duree / 6)
        logger.debug("Estimation du nombre de fragments: %d" % (self.nbFragMax))

        # Ajout des fragments
        logger.info("Début du téléchargement des fragments")
        try:
            i = self.premierFragment
            self.navigateur.appendCookie("hdntl", self.hdntl)
            while(not self.stopDownloadEvent.isSet()):
                frag = self.navigateur.getFichier("%s%d" % (self.urlFrag, i), referer = self.adobePlayer)
                debut = self.debutVideo(i, frag)
                self.fichierVideo.write(frag[debut :])
                # Affichage de la progression
                self.progressFnct(min(int((i / self.nbFragMax) * 100), 100))
                i += 1
        except urllib2.URLError, e:
            if(hasattr(e, 'code')):
                if(e.code == 403):
                    if(e.reason == "Forbidden"):
                        logger.info("Le hash du player semble invalide ; calcul du nouveau hash")
                        newPlayerHash = self.getPlayerHash()
                        if(newPlayerHash != self.playerHash):
                            self.configuration["player_hash"] = newPlayerHash
                            self.configuration.writeConfig()
                            logger.info("Un nouveau hash a été trouvé ; essayez de relancer l'application")
                        else:
                            logger.critical("Pas de nouveau hash disponible...")
                    else:
                        logger.critical("Impossible de charger la vidéo")
                elif(e.code == 404):
                    self.progressFnct(100)
                    self.telechargementFini = True
                    logger.info("Fin du téléchargement")
        except KeyboardInterrupt:
            logger.info("Interruption clavier")
        except:
            logger.critical("Erreur inconnue")
        finally:
            # Ajout dans l'historique
            self.historique.ajouter(Video(lien = self.urlFrag,
                                          fragments = i,
                                          finie = self.telechargementFini))
            # Fermeture du fichier
            self.fichierVideo.close()
