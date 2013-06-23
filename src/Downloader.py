#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation des protocoles de téléchargements utilisés pour les sites de 
# replay/catch-up TV.

#
# Modules
#

import os
import subprocess
import shlex
import datetime

# Pour éviter les erreurs:
# UnicodeEncodeError: 'ascii' codec can't encode character u'\xe9' in position 213: ordinal not in range(128)
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur

import logging
logger = logging.getLogger("replaydlr")

class DownloaderException(Exception):
    """
    Exception levée par ReplayDl/Downloader
    """
    pass

class Downloader(object):
    """
    Classe virtuelle de téléchargement.
    """
    def __init__(self,
                 outDir,
                 codeProgramme,
                 timeStamp,
                 extension,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.outDir = outDir
        self.codeProgramme = codeProgramme
        self.timeStamp = timeStamp
        self.navigateur = navigateur
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct
        self.nomFichier = self.getNomFichier(extension)

    def getNomFichier(self, extension):
        """
        Construit le nom du fichier de sortie
        """
        nomFichier = os.path.join(
            self.outDir, "%s_%s.%s" % (
                self.codeProgramme,  # enlever [ !:;?/<>] ?
                datetime.datetime.fromtimestamp(self.timeStamp).strftime(
                    "%Y-%m-%d_%H-%M"),
                extension))
        logger.debug(nomFichier)
        return nomFichier

    def ouvrirNouvelleVideo(self):
        """
        Créer une nouvelle vidéo
        """
        try:
            # Ouverture du fichier
            self.fichierVideo = open(self.nomFichier, "wb")
        except:
            raise DownloaderException(
                "Impossible d'écrire dans le répertoire %s" % (self.outDir))

    def ouvrirVideoExistante(self):
        """
        Ouvre une vidéo existante
        """
        try:
            # Ouverture du fichier
            self.fichierVideo = open(self.nomFichier, "a+b")
        except:
            raise DownloaderException(
                "Impossible d'écrire dans le répertoire %s" % (self.outDir))

    def telecharger(self):
        """
        Effectue le téléchargement (virtuelle ← dépend du protocole)
        """
        pass

    def convertir(self,         # À REPRENDRE: os.system → subprocess
                  videoCodec='copy',
                  audioCodec='copy'):
        """
        Convertit la vidéo téléchargée dans le format final:
        - crée l'en-tête de la vidéo
        - rajoute les méta-data
        - inclut les sous-titres s'il y en a (à faire, donc!)
        """

        # todo:
        # appel par subprocess
        # vérif de ffmpeg
        # gestion des sous-titres
        # split du titre sur '-' si possible → title/artist
        logger.info("Conversion de la vidéo dans le format final; veuillez attendre quelques instants")
        fichierFinal = self.getNomFichier("mp4")
        inCmd = '-i "%s" -vcodec %s -acodec %s -metadata title="%s" -metadata artist="%s" -metadata album="%s" -metadata date="%s" -metadata comment="%s" "%s"' % (
            self.nomFichier,    # input
            videoCodec,
            audioCodec,
            self.codeProgramme, # titre → title
            '',                 # → artist
            datetime.datetime.fromtimestamp(self.timeStamp).strftime(
                "%d/%m"),       # date jour/mois → album
            datetime.datetime.fromtimestamp(self.timeStamp).strftime(
                "%Y"),          # année → date (y'a'k'ça qui rentre?;)
            u'Obtenu avec replaydlr 😎', # → comment
            fichierFinal)
        try:
            if(os.name == "nt"):
                commande = "ffmpeg.exe %s 1>NUL 2>NUL" % (inCmd)
            else:
                commande = "ffmpeg %s 1>/dev/null 2>/dev/null" % (inCmd)
            logger.debug(commande)
            if(os.system(commande) == 0):
                os.remove(self.nomFichier)
                logger.info("Fin !")
            else:
                # pour les erreurs:
# Application provided invalid, non monotonically increasing dts to muxer in stream 1: 1859584 >= 1859584
# av_interleaved_write_frame(): Invalid argument
                # rappel pour recodage, mais c'est BEAUCOUP plus long...
                if videoCodec == 'copy' and audioCodec == 'copy':
                    logger.warning("La vidéo nécessite un ré-encodage complet (et long); veuillez patienter")
                    try:
                        os.remove(fichierFinal)
                    except:
                        pass
                    self.convertir('libx264', 'libvo_aacenc')
                else:
                    logger.warning("Problème lors de la conversion avec FFmpeg ; le fichier %s est néanmoins disponible" % (self.nomFichier))
        except:
                raise DownloaderException("Impossible de créer la vidéo finale")

    def checkExternalProgram(self, prog, optArg='', expectedValue=''):
        """
        Permet de vérifier la présence des programmes externes requis
        """
        logger.debug('→checkExternalProgram(%s, %s, %s)'% (
                prog, optArg, expectedValue))
        args=shlex.split('%s %s' % (prog, optArg))
        try:
            process=subprocess.Popen(args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            stdout, stderr = process.communicate()
            if expectedValue == '':
                return True
            else:
                if expectedValue in stdout: # à améliorer pour versions > ...
                    return True
                else:
                    return False
        except OSError:
            logger.error('Le programme %s n\'est pas présent sur votre système' % (prog))
        return False
