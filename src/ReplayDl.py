#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Définition d'une classe virtuelle pour les téléchargements depuis les sites
# de replay/catch-up TV.
# Les classes spécifiques à chaque site héritent de celle-ci.

#
# Modules
#

import datetime
import os
import threading

from Configuration  import Configuration
from Historique     import Historique, Video
from Navigateur     import Navigateur
from Downloader     import Downloader
from DownloaderM3u8 import DlM3u8
from DownloaderF4m  import DlF4m
from DownloaderRtmp import DlRtmp
from DownloaderMms  import DlMms
from DownloaderCurl import DlCurl

import logging
logger = logging.getLogger("replaydlr")

#
# Classes
#

class ReplayDlException(Exception):
    """
    Exception levée par ReplayDl
    """
    pass


class ReplayDl(object):
    """
    Classe principale pour lancer un téléchargement
    """

    def __init__(self,
                 url,                # URL de la video
                 proxy = None,       # Proxy à utiliser
                 proxySock = False,  # Proxy est-il de type SOCK?
                 sousTitres = False, # Télécharger les sous-titres?
                 progressFnct = lambda x: None, # Callback de progression
                 stopDownloadEvent = threading.Event(), # → Arrêt
                 outDir = "."        # Répertoire de sortie
                 ):
        # Classe pour télécharger des fichiers
        self.url = url
        self.navigateur = Navigateur(proxy, proxySock)
        self.pageHtml= None
        # Infos vidéo récupérées (dans la page, le xml, ou le json...)
        self.id = None
        self.lienMms = None
        self.lienRtmp = None
        self.lienCurl = None
        self.manifestUrl = None
        self.manifestUrlToken = None
        self.m3u8Url = None
        self.drm = None
        self.chaine = None
        self.timeStamp = None
        self.codeProgramme = None

        # Récupère la page html
        self.pageHtml = self.navigateur.getFichier(url)
        # Récupère les infos requises
        self.getInfos()          # virtuelle
        # Petit message en cas de DRM
        if self.drm == "oui":
            logger.warning("La vidéo possède un DRM; elle sera sans doute illisible.")
        # Le téléchargement s'effectue en fonction du type de lien disponible
        if self.manifestUrl is not None:
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme,
                                            self.timeStamp, "flv")
            # Downloader
            downloader = DlF4m(self.manifestUrl, self.manifestUrlToken,
                               nomFichier, self.navigateur,
                               stopDownloadEvent, progressFnct)
        elif self.m3u8Url is not None:
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme,
                                            self.timeStamp, "ts")
            # Downloader
            downloader = DlM3u8(self.m3u8Url, nomFichier,
                                self.navigateur,stopDownloadEvent,
                                progressFnct)
        elif self.lienRtmp is not None:
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme,
                                            self.timeStamp, "flv")
            # Downloader
            downloader = DlRtmp(self.lienRtmp, nomFichier,
                                self.navigateur, stopDownloadEvent,
                                progressFnct)
        elif self.lienMms is not None:
            # Nom du fichier
            # Downloader
            downloader = DlMms(self.lienMms)
        elif self.lienCurl:
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme,
                                            self.timeStamp, "mp4")
            # Downloader
            downloader = DlCurl(self.lienCurl, nomFichier,
                                self.navigateur, stopDownloadEvent,
                                progressFnct)
        else:                   #  pas de lien connu détecté
            raise ReplayDlException("Aucun lien vers la vidéo!")

        # Récupère les sous-titres si possible
        if(sousTitres):
            self.telechargerSousTitres(self.id, self.chaine, nomFichier)
        # Lance le téléchargement
        downloader.telecharger()
        #self.convertir() # ?

    def getInfos(self):
        """
        Cette méthode virtuelle doit être surchargée en fonction du site ciblé.
        Elle est chargée de récupérer toutes les informations nécessaires au
        téléchargement:
        - id de la vidéo
        - type de téléchargement
        - lien de téléchargement
        ...
        """
        pass

    def getNomFichier(self, repertoire, codeProgramme, timeStamp, extension):
        """
        Construit le nom du fichier de sortie
        """
        logger.debug(os.path.join(repertoire, "%s_%s.%s" % (codeProgramme, datetime.datetime.fromtimestamp(timeStamp).strftime("%Y-%m-%d_%H-%M"), extension))) # TBR!
        return os.path.join(repertoire, "%s_%s.%s" % (codeProgramme, datetime.datetime.fromtimestamp(timeStamp).strftime("%Y-%m-%d_%H-%M"), extension))

    def telechargerSousTitres(self, idEmission, nomChaine, nomVideo):
        """
        Récupère le fichier de sous titre de la vidéo.
        Virtuelle ← spécifique à Pluzz
        """
        pass
