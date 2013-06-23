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

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur

import logging
logger = logging.getLogger("pluzzdl")

class DownloaderException(Exception):
    """
    Exception levée par ReplayDl/Downloader
    """
    pass

class Downloader(object):
    """
    Classe virtuelle de téléchargement.
    """
    def __init__(self):
        pass                    # il y a des initialisations factorisables!

    def ouvrirNouvelleVideo(self):
        """
        Créer une nouvelle vidéo
        """
        try:
            # Ouverture du fichier
            self.fichierVideo = open(self.nomFichier, "wb")
        except:
            raise DownloaderException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))

    def ouvrirVideoExistante(self):
        """
        Ouvre une vidéo existante
        """
        try:
            # Ouverture du fichier
            self.fichierVideo = open(self.nomFichier, "a+b")
        except:
            raise DownloaderException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))

    def telecharger(self):
        """
        Effectue le téléchargement (virtuelle ← dépend du protocole)
        """
        pass

    def convertir(self): # À REPRENDRE → os.system, appel APRÈS telecharger...
        """
        Convertit la vidéo téléchargée dans le format final (cree l'en-tete de la video)
        """
        logger.info("Conversion de la vidéo dans le format final; veuillez attendre quelques instants")
        try:
            if(os.name == "nt"):
                commande = "ffmpeg.exe -i %s -vcodec copy -acodec copy %s 1>NUL 2>NUL" % (self.nomFichier, self.nomFichierFinal)
            else:
                commande = "ffmpeg -i %s -vcodec copy -acodec copy %s 1>/dev/null 2>/dev/null" % (self.nomFichier, self.nomFichierFinal)
            if(os.system(commande) == 0):
                os.remove(self.nomFichier)
                logger.info("Fin !")
            else:
                logger.warning("Problème lors de la création du MKV avec FFmpeg ; le fichier %s est néanmoins disponible" % (self.nomFichier))
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
