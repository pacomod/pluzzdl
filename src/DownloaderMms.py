#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Implémentation du téléchargement des lien mms

#
# Modules
#

# Pour éviter les erreurs:
# UnicodeEncodeError: 'ascii' codec can't encode character u'\xe9' in position 213: ordinal not in range(128)
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

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

    def __init__(self,
                 lienMms,
                 outDir,
                 codeProgramme,
                 timeStamp,
                 navigateur,
                 stopDownloadEvent,
                 progressFnct):
        self.lien = lienMms
        super(DlMms, self).__init__(outDir, codeProgramme, timeStamp, "t.flv",
                                    navigateur, stopDownloadEvent, progressFnct)

    def telecharger(self):
        logger.info("Lien MMS: %s\nUtiliser par exemple mimms ou msdl pour la récupérer directement" % (self.lien))

