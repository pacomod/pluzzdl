#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du téléchargement des lien mms

#
# Modules
#

from Configuration import Configuration
from Historique    import Historique, Video
from Navigateur    import Navigateur
from Downloader    import Downloader, DownloaderException

import logging
logger = logging.getLogger("replaydlr")

class DlMms(Downloader):
    """
    Téléchargement des liens mms
    """

    def __init__(self, lienMms):
        self.lien = lienMms

    def telecharger(self):
        logger.info("Lien MMS: %s\nUtiliser par exemple mimms ou msdl pour la récupérer directement" % (self.lien))

