#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du téléchargement des liens rtmp

#
# Modules
#

import subprocess
import shlex
import time
import threading

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from Downloader    import Downloader, DownloaderException

import logging
logger = logging.getLogger("replaydlr")

class DlRtmp(Downloader):
    """
    Téléchargement des liens rtmp
    """

    swfPlayerUrl = 'http://www.wat.tv/images/v60/PlayerWat.swf'
    rtmpdumpEx='rtmpdump'

    def __init__(self,
                 lienRtmp,
                 nomFichier,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.nomFichier = nomFichier
        self.navigateur = navigateur
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct
        self.lienRtmp = lienRtmp

    def telecharger(self):
        if not self.checkExternalProgram(self.rtmpdumpEx):
            logger.warning('Ce script requiert %s' % (self.rtmpdumpEx))
        elif self.rtmpDownload(self.lienRtmp, False) == 0:
            logger.info('Téléchargement terminé')
        else:
            logger.info('Problème réseau ou algo?')
            
        # logger.info("Lien RTMP: %s\nUtiliser par exemple rtmpdump pour la récupérer directement" % (self.lienRtmp))

    def rtmpDownload(self,
                     rtmpUrl,
                     swfForceRefresh):
        """
        Appel de rtmpdump avec traitement des options et reprise (récursif)
        """
        logger.debug('→rtmpDownload(%s, %s)' % (
                rtmpUrl, swfForceRefresh))
        rtmpCmd = '%s --resume --rtmp "%s" --port 1935 --timeout 10' % (
            self.rtmpdumpEx, rtmpUrl)    # initialisation de la commande

        if swfForceRefresh:
            rtmpCmd += ' --swfVfy %s --swfAge 0' % (self.swfPlayerUrl)
        else:
            rtmpCmd += ' --swfVfy %s' % (self.swfPlayerUrl)
        rtmpCmd += ' -o "%s"' % (self.nomFichier)
        logger.info(rtmpCmd)
        rtmpCall = shlex.split(rtmpCmd)
        rtmpProc = subprocess.Popen(rtmpCall,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
        (stdout, stderr) = rtmpProc.communicate()
        if rtmpProc.returncode == 1:   # sortie en erreur →
            logger.debug('rtmpdump output: %s' % (stdout))
            if 'corrupt file!' in stdout: # ERROR: Last tag...corrupt file!
                logger.warning('Le fichier %s est corrompu!\n\t le téléchargement doit reprendre du début...' % (self.nomFichier))
                os.remove(self.nomFichier)
                return self.rtmpDownload(rtmpUrl, swfForceRefresh)
            else:                      # ERROR: RTMP_ReadPacket...?
                if not swfForceRefresh: # on ré-essaye en forçant le recalcul
                    return self.rtmpDownload(rtmpUrl, True)
                else:               # rtmpdump computation & refresh KO →
                    logger.warning ('Veuillez ré-essayer plus tard...')
        elif rtmpProc.returncode == 2:   # téléchargement incomplet →
            logger.info('Téléchargement incomplet: nouvel essai dans 3s...')
            time.sleep(3)                # petite temporisation
            if swfForceRefresh:   # pas la peine de le refaire
                return self.rtmpDownload(rtmpUrl, False)
            else:                   # on rappelle avec les mêmes options
                return self.rtmpDownload(rtmpUrl, swfForceRefresh)
        else:
            return rtmpProc.returncode # = 0
