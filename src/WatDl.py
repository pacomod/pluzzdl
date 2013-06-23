#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Notes :
#    -> Filtre Wireshark :
#          http.host contains "ftvodhdsecz" or http.host contains "francetv" or http.host contains "pluzz"
#    ->

#
# Modules
#

import bs4 as  BeautifulSoup
import os
import re
import threading
import time
import xml.etree.ElementTree
import xml.sax
from urlparse import urlparse
import json
import md5
import locale

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

class WatDl(ReplayDl):
    """
    Classe principale pour lancer un téléchargement Wat (tf1, tmc, nt1, hd1)
    """
    WEBROOTWAT = "http://www.wat.tv"
    wat_url = "/web/"

    def __init__(self,
                 url,                # URL de la video
                 proxy = None,       # Proxy à utiliser
                 proxySock = False,  # Proxy est-il de type SOCK?
                 sousTitres = False, # Télécharger les sous-titres?
                 progressFnct = lambda x: None, # Callback de progression
                 stopDownloadEvent = threading.Event(), # → Arrêt
                 outDir = ".",       # Répertoire de sortie
                 stardardDefinition = False # → ne pas chercher la HD
                 ):
        self.stardardDefinition = stardardDefinition
        self.hasHD = False
        self.standardDefinition = False
        self.listOfIds = []
        self.referer = None
        super(WatDl, self).__init__(url, proxy, proxySock, sousTitres,
                                    progressFnct, stopDownloadEvent, outDir)

    def getInfos(self):
        """
        Méthode virtuelle de ReplayDl surchargée spécifiquement pour Wat
        """
        # Récupère l'id de l'émission
        debut_id = ''
        soup = BeautifulSoup.BeautifulSoup(self.pageHtml) #, from_encoding='utf-8')
        # logger.debug('la soupe: \n%s' % (soup)) # TBR!
        site = urlparse(self.url).netloc
        if 'tmc.tv' in site or 'tf1.fr' in site:
            debut_id = str(soup.find('div', attrs={'class' : 'unique' }))
            
        if 'nt1.tv' in site or 'hd1.tv' in site:
            debut_id = str(soup.find('section', attrs={'class' : 'player-unique' }))
        # recherche de la date de diffusion
        if 'nt1.tv' in site:
            dateDiffusion= soup.find('span', attrs={'class' : 'date'}).getText()
            logger.debug('dateDiffusion=%s' % (dateDiffusion))
            locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')
            self.timeStamp = time.mktime(
                time.strptime(
                    soup.find('span', attrs={'class' : 'date'}).getText(),
                    "Le %d %b %Y \xe0 %Hh%M")) # \xe0 # ou "%d %B %Y à %Hh%M"? <juillet
            # S'il n'y a pas moyen de corriger le pb d'encodage
            # passer par le json (paske ça commence à saouler!)
        elif 'tf1.fr' in site:
            # →TBR!
            dateDiffusion = soup.find('meta', attrs={'property' : 'video:release_date'}).get('content')
            logger.debug('date=%s' % (dateDiffusion))
            # ←TBR!
            locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')
            self.timeStamp = time.mktime(
                time.strptime(
                    dateDiffusion[: -5], # \+0200 # TBR!
                    "%Y-%m-%dT%H:%M:%S"))
        elif 'hd1.tv' in site:
            dateDiffusion= soup.find('span', attrs={'class' : 'date'}).getText()
            logger.debug('date=%s' % (dateDiffusion))
            locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')
            self.timeStamp = time.mktime(
                time.strptime(
                    soup.find('span', attrs={'class' : 'date'}).getText(),
                    'Le %d %b %Y \xe0 %Hh%M')) # ou "%d %B %Y à %Hh%M"? <juillet
            
        elif 'tmc.tv' in site:  # → dans le json
            pass
        
        self.id = [x.strip() for x in re.findall("mediaId :([^,]*)",
                                                 debut_id)][0]
        self.referer = [x.strip() for x in re.findall('url : "(.*?)"',
                                                      debut_id)][0]
        self.getJsonInfos()

    def getJsonInfos(self):
        jsonVideoInfos = self.navigateur.getFichier(
            self.WEBROOTWAT+'/interface/contentv3/'+ self.id,
            self.referer)
        # logger.debug('le json: \n%s' % (jsonVideoInfos)) # TBR!
        videoInfos = json.loads(jsonVideoInfos)
        if not self.standardDefinition:
            try:
                self.hasHD = videoInfos["media"]["files"][0]["hasHD"]
            except:
                self.hasHD = False
        else:
            self.hasHD = False

        # Recherche de la date de diffusion
        if self.timeStamp is None:
            # →TBR!
            dateDiffusion = videoInfos["media"]["chapters"][0]['date_diffusion']
            logger.error('date=%s' % (dateDiffusion))
            # ←TBR!
            self.timeStamp = time.mktime(
                time.strptime(
                    dateDiffusion + 'T13:42', # +T13:42 # TBR!
                    "%d/%m/%YT%H:%M"))

        # Titre de la vidéo
        self.codeProgramme = videoInfos["media"]["title"] # /!\ espaces /!\

        NumberOfParts = len(videoInfos["media"]["files"])
        for iPart in range(NumberOfParts):
            self.listOfIds.append(videoInfos["media"]["files"][iPart]["id"])
        # comment gérer cette boucle pour le téléchargement?
        id_url1 = self.getWat(self.listOfIds[0], self.hasHD)
        data=self.navigateur.getFichier(id_url1, self.referer)
        if data[0:4] == 'http':
            self.lienCurl = data
        elif data[0:4] == 'rtmp':
            if '.hd' in data:
                rtmpUrl = re.search('rtmpte://(.*)hd', data).group(0)
            if '.h264' in data:
                rtmpUrl = re.search('rtmpte://(.*)h264', data).group(0)
            self.lienRtmp = rtmpUrl.replace('rtmpte','rtmpe')

    def getWat(self, idVideo, hasHD):
        """
        Fonction qui permet de retrouver une video sur wat
        """
        def base36encode(number):
            if not isinstance(number, (int, long)):
                raise TypeError('number must be an integer')
            if number < 0:
                raise ValueError('number must be positive')
            alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            base36 = ''
            while number:
                number, i = divmod(number, 36)
                base36 = alphabet[i] + base36
            return base36 or alphabet[0]
        if hasHD:
            self.wat_url = "/webhd/"
        else:
            self.wat_url = "/web/"
        ts = base36encode(int(time.time())-60)
        timesec = hex(int(ts, 36))[2:]
        while(len(timesec)<8):
            timesec = "0"+timesec
        token = md5.new(
            "9b673b13fa4682ed14c3cfa5af5310274b514c4133e9b3a81e6e3aba00912564" +
            self.wat_url + str(idVideo) + "" + timesec).hexdigest()
        id_url1 = (self.WEBROOTWAT + "/get" + self.wat_url + str(idVideo) +
                   "?token=" + token + "/" + str(timesec) +
                   "&country=FR&getURL=1")
        return id_url1

