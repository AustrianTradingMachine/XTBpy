#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    XTBpy, a wrapper for the API of XTB (https://www.xtb.com)
#
#    Copyright (C) 2024  Philipp Craighero
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###########################################################################

import XTB
from pathlib import Path
from threading import Thread
import time
from datetime import datetime, timedelta


# Setting DEMO to True will use the demo account
DEMO=True

# just example how to generate alogger. Feel free to use your own logger
logger=XTB.generate_logger(name="TEST",path=Path('~/Logger/XTBpy'))


# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)


# Target function for Ticker
def Ticker(later: datetime):

    exchange=XTBData.streamTickPrices(symbol='ETHEREUM', minArrivalTime=0, maxLevel=1)

    while datetime.now() < later:
        exchange['lock'].acquire(blocking=True)
        if not exchange['df'].empty:
            print(exchange['df'].to_string(index=False, header=False))
            exchange['df'] = exchange['df'].iloc[0:0]
        exchange['lock'].release()
        time.sleep(1)

    exchange['thread'].start()


# Target function for Candles
def Candles(later: datetime):

    exchange=XTBData.streamCandles(symbol='ETHEREUM')

    while datetime.now() < later:
        exchange['lock'].acquire(blocking=True)
        if not exchange['df'].empty:
            print(exchange['df'].to_string(index=False, header=False))
            exchange['df'] = exchange['df'].iloc[0:0]
        exchange['lock'].release()
        time.sleep(1)

    exchange['thread'].start()


# Defining streaming threads
TickerThread = Thread(target=Ticker, args=(datetime.now()+timedelta(seconds=60*1),), daemon=True)
CandlesThread = Thread(target=Candles, args=(datetime.now()++timedelta(seconds=60*1),), daemon=True)


# Starting streaming threads
TickerThread.start()
CandlesThread.start()





# Close Wrapper
XTBData.delete()