#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du protocole de téléchargement par m3u8

#
# Modules
#

import os
import re

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from Downloader    import Downloader, DownloaderException

import logging
logger = logging.getLogger("replaydlr")

class DlM3u8(Downloader):
    """
    Téléchargement des liens m3u8
    """

    def __init__(self,
                 m3u8Url,
                 nomFichier,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.m3u8Url = m3u8Url
        self.nomFichier = nomFichier
        self.navigateur = navigateur
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct

        self.historique = Historique()

        self.nomFichierFinal = "%s.mkv" % (self.nomFichier[:-3])


    def telecharger(self):
        # Récupère le fichier master.m3u8
        self.m3u8 = self.navigateur.getFichier(self.m3u8Url)
        # Extrait l'URL de tous les fragments
        self.listeFragments = re.findall(".+?\.ts", self.m3u8)
        #
        # Création de la vidéo
        #
        self.premierFragment = 1
        self.telechargementFini = False
        video = self.historique.getVideo(self.m3u8Url)
        # Si la vidéo est dans l'historique
        if(video is not None):
            # Si la vidéo existe sur le disque
            if(os.path.exists(self.nomFichier) or
               os.path.exists(self.nomFichierFinal)):
                if(video.finie):
                    logger.info("La vidéo a déjà été entièrement téléchargée")
                    if(not os.path.exists(self.nomFichierFinal)):
                        self.convertir()
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
        # Nombre de fragments
        self.nbFragMax = float(len(self.listeFragments))
        logger.debug("Nombre de fragments: %d" % (self.nbFragMax))
        # Ajout des fragments
        logger.info("Début du téléchargement des fragments")
        try:
            i = self.premierFragment
            while(i <= self.nbFragMax and not self.stopDownloadEvent.isSet()):
                frag = self.navigateur.getFichier("%s" % (
                        self.listeFragments[i - 1]))
                self.fichierVideo.write(frag)
                # Affichage de la progression
                self.progressFnct(min(int((i / self.nbFragMax) * 100), 100))
                i += 1
            if(i == self.nbFragMax + 1):
                self.progressFnct(100)
                self.telechargementFini = True
                logger.info("Fin du téléchargement")
                self.convertir()
        except KeyboardInterrupt:
            logger.info("Interruption clavier")
        except Exception as inst:
            logger.critical("Erreur inconnue %s" % inst)
        finally:
            # Ajout dans l'historique
            self.historique.ajouter(Video(lien = self.m3u8Url, fragments = i,
                                          finie = self.telechargementFini))
            # Fermeture du fichier
            self.fichierVideo.close()

