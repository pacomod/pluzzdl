#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Notes :
#    -> Filtre Wireshark :
#          http.host contains "ftvodhdsecz" or http.host contains "francetv" or http.host contains "pluzz"
#    ->

#
# Modules
#

import BeautifulSoup
import os
import re
import threading
import time
import xml.etree.ElementTree
import xml.sax

# Pour éviter les erreurs:
# UnicodeEncodeError: 'ascii' codec can't encode character u'\xe9' in position 213: ordinal not in range(128)
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from ReplayDl      import ReplayDl, ReplayDlException

import logging
logger = logging.getLogger("replaydlr")

#
# Classes
#

class PluzzDl(ReplayDl):
    """
    Classe principale pour lancer un téléchargement Pluzz
    """

    REGEX_ID = "http://info.francetelevisions.fr/\?id-video=([^\"]+)"
    XML_DESCRIPTION = "http://www.pluzz.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=_ID_EMISSION_"
    URL_SMI = "http://www.pluzz.fr/appftv/webservices/video/getFichierSmi.php?smi=_CHAINE_/_ID_EMISSION_.smi&source=azad"
    M3U8_LINK = "http://medias2.francetv.fr/catchup-mobile/france-dom-tom/non-token/non-drm/m3u8/_FILE_NAME_.m3u8"
    REGEX_M3U8 = "/([0-9]{4}/S[0-9]{2}/J[0-9]{1}/[0-9]*-[0-9]{6,8})-"

    def __init__(self,
                 url,                # URL de la video
                 proxy = None,       # Proxy à utiliser
                 proxySock = False,  # Proxy est-il de type SOCK?
                 sousTitres = False, # Télécharger les sous-titres?
                 progressFnct = lambda x: None, # Callback de progression
                 stopDownloadEvent = threading.Event(), # → Arrêt
                 outDir = "."        # Répertoire de sortie
                 ):
        super(PluzzDl, self).__init__(url, proxy, proxySock, sousTitres,
                                      progressFnct, stopDownloadEvent, outDir)

    def getInfos(self):
        """
        Méthode virtuelle de ReplayDl surchargée spécifiquement pour Pluzz
        """
        # Récupère l'id de l'émission
        self.getId()
        # Récupère la page d'infos de l'émission
        pageInfos = self.navigateur.getFichier(self.XML_DESCRIPTION.replace("_ID_EMISSION_", self.id))
        # Parse la page d'infos
        self.parseInfos(pageInfos)

    def getId(self):
        """
        Récupère l'ID de la vidéo à partir de son URL
        """
        # try:
        self.id = re.findall(self.REGEX_ID, self.pageHtml)[0]
        logger.debug("ID de l'émission: %s" % (self.id))
        # except:
        #     raise ReplayDlException("Impossible de récupérer l'ID de l'émission")

    def parseInfos(self, pageInfos):
        """
        Parse le fichier de description XML d'une émission
        """
        try:
            xml.sax.parseString(pageInfos, PluzzDLInfosHandler(self))
            # Si le lien m3u8 n'existe pas, il faut essayer de créer celui
            # de la plateforme mobile
            if(self.m3u8Url is None):
                logger.debug("m3u8Url file missing, we will try to guess it")
                if(self.manifestUrl is not None):
                    # Vérifie si le lien du manifest contient la chaîne "media-secure"
                    if(self.manifestUrl.find("media-secure") != -1):
                        self.drm = True
                        #raise ReplayDlException("pluzzdl ne sait pas gérer ce type de vidéo (utilisation de DRMs)...")
                    # Lien du manifest (après le token)
                    self.manifestUrlToken = self.navigateur.getFichier("http://hdfauth.francetv.fr/esi/urltokengen2.html?url=%s" % (self.manifestUrl[self.manifestUrl.find("/z/") :]))
                    self.m3u8Url = self.manifestUrl.replace("manifest.f4m", "index_2_av.m3u8")
                    self.m3u8Url = self.m3u8Url.replace("/z/", "/i/")
                #self.m3u8Url = self.M3U8_LINK.replace("_FILE_NAME_", re.findall(self.REGEX_M3U8, pageInfos)[0])
            logger.debug("URL m3u8: %s" % (self.m3u8Url))
            logger.debug("URL manifest: %s" % (self.manifestUrl))
            logger.debug("Lien RTMP: %s" % (self.lienRtmp))
            logger.debug("Lien MMS: %s" % (self.lienMms))
            logger.debug("Utilisation de DRM: %s" % (self.drm))
        except:
            raise ReplayDlException("Impossible de parser le fichier XML de l'émission")

    def telechargerSousTitres(self, idEmission, nomChaine, nomVideo):
        """
        Récupère le fichier de sous-titres de la vidéo
        """
        urlSousTitres = self.URL_SMI.replace("_CHAINE_", nomChaine.lower().replace(" ", "")).replace("_ID_EMISSION_", idEmission)
        # Essaye de récupérer les sous-titres
        try:
            sousTitresSmi = self.navigateur.getFichier(urlSousTitres)
        except:
            logger.debug("Sous-titres indisponibles")
            return
        logger.debug("Sous-titres disponibles")
        # Enregistre le fichier de sous-titres en smi
        try:
            (nomFichierSansExtension, _) = os.path.splitext(nomVideo)
            # Écrit le fichier
            with open("%s.smi" % (nomFichierSansExtension), "w") as f:
                f.write(sousTitresSmi)
        except:
            raise ReplayDlException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
        logger.debug("Fichier de sous-titres smi enregistré")
        # Convertit le fichier de sous-titres en srt
        try:
            with open("%s.srt" % (nomFichierSansExtension), "w") as f:
                pageSoup = BeautifulSoup.BeautifulSoup(sousTitresSmi)
                elmts = pageSoup.findAll("sync")
                indice = 1
                for (elmtDebut, elmtFin) in (elmts[i: i + 2] for i in range(0, len(elmts), 2)):
                    # Extrait le temps de début et le texte
                    tempsEnMs = int(elmtDebut["start"])
                    tempsDebutSrt = time.strftime("%H:%M:%S,XXX", time.gmtime(int(tempsEnMs / 1000)))
                    tempsDebutSrt = tempsDebutSrt.replace("XXX", str(tempsEnMs)[-3 :])
                    lignes = elmtDebut.p.findAll("span")
                    texte = "\n".join(map(lambda x: x.contents[0].strip(), lignes))
                    # Extrait le temps de fin
                    tempsEnMs = int(elmtFin["start"])
                    tempsFinSrt = time.strftime("%H:%M:%S,XXX", time.gmtime(int(tempsEnMs / 1000)))
                    tempsFinSrt = tempsFinSrt.replace("XXX", str(tempsEnMs)[-3 :])
                    # Écrit dans le fichier
                    f.write("%d\n" % (indice))
                    f.write("%s --> %s\n" % (tempsDebutSrt, tempsFinSrt))
                    f.write("%s\n\n" % (texte.encode("iso-8859-1")))
                    # élément suivant
                    indice += 1
        except:
            logger.error("Impossible de convertir les sous-titres en str")
            return
        logger.debug("Fichier de sous titre-srt enregistré")


class PluzzDLInfosHandler(xml.sax.handler.ContentHandler):
    """
    Handler pour parser le XML de description d'une émission
    """

    def __init__(self, pluzzdl):
        self.pluzzdl = pluzzdl

        self.isUrl = False
        self.isDRM = False
        self.isChaine = False
        self.isCodeProgramme = False

    def startElement(self, name, attrs):
        if(name == "url"):
            self.isUrl = True
        elif(name == "drm"):
            self.isDRM = True
        elif(name == "chaine"):
            self.isChaine = True
        elif(name == "diffusion"):
            self.pluzzdl.timeStamp = float(attrs.getValue("timestamp"))
        elif(name == "code_programme"):
            self.isCodeProgramme = True

    def characters(self, data):
        if(self.isUrl):
            if(data[: 3] == "mms"):
                self.pluzzdl.lienMms = data
            elif(data[: 4] == "rtmp"):
                self.pluzzdl.lienRtmp = data
            elif(data[-3 :] == "f4m"):
                self.pluzzdl.manifestUrl = data
            elif(data[-4 :] == "m3u8"):
                self.pluzzdl.m3u8Url = data
        elif(self.isDRM):
            self.pluzzdl.drm = data
        elif(self.isChaine):
            self.pluzzdl.chaine = data
        elif(self.isCodeProgramme):
            self.pluzzdl.codeProgramme = data

    def endElement(self, name):
        if(name == "url"):
            self.isUrl = False
        elif(name == "drm"):
            self.isDRM = False
        elif(name == "chaine"):
            self.isChaine = False
        elif(name == "code_programme"):
            self.isCodeProgramme = False
