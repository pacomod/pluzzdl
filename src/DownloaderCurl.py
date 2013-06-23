#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du téléchargement des liens curl

#
# Modules
#

import subprocess
import shlex
import threading

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from Downloader    import Downloader, DownloaderException

import logging
logger = logging.getLogger("pluzzdl")

class DlCurl(Downloader):
    """
    Téléchargement des liens curl
    """

    def __init__(self,
                 lienCurl,
                 nomFichier,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.lienCurl = lienCurl
        self.nomFichier = nomFichier
        self.navigateur = navigateur
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct

    def telecharger(self):
        curlEx='curl'
        if not self.checkExternalProgram(curlEx):
            logger.warning('Ce script requiert %s' % (curlEx))
        else:
            curlCmd = '%s "%s" -C - -L -g -A "%s" -o "%s"' % (
                curlEx, self.lienCurl, self.navigateur.userAgent, self.nomFichier)
            logger.debug(curlCmd)
            isDownloaded = False
            while not isDownloaded:
                curlProc = subprocess.Popen(curlCmd,
                                            stdout=subprocess.PIPE,
                                            shell=True)
                (stdout, stderr) = curlProc.communicate()
                if curlProc.returncode == 0:
                    isDownloaded = True
                else:
                    logger.debug('curl output:%s' % (stdout))
                    if 'Cannot resume' in stdout:
                        logger.warning('Le fichier obtenu est complet ou corrompu')
                        isDownloaded = True # pour sortir quand même...

        # logger.info("Lien curl: %s\nUtiliser par exemple curl pour la récupérer directement" % (self.lien))

