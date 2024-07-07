import logging
import os
import pandas as pd
from threading import Lock
import configparser
import datetime
from dateutil.relativedelta import relativedelta
import pytz
from XTB.handler import HandlerManager
from XTB.utils import generate_logger, signum, calculate_timedelta


# read api configuration
config = configparser.ConfigParser()
config.read('XTB/api.cfg')

SEND_INTERVAL=config.getint('CONNECTION','SEND_INTERVAL')


class Wrapper(HandlerManager):
    """
    Wrapper class for XTB API.

    Attributes:
        _demo (bool): Flag indicating whether the demo environment is used.
        _logger (logging.Logger): Logger instance for logging messages.
        _utc_tz (pytz.timezone): Timezone for UTC.
        _cest_tz (pytz.timezone): Timezone for Europe/Berlin.
        _deleted (bool): Flag indicating whether the wrapper has been deleted.

    Methods:
        __init__(self, demo: bool=True, logger=None): Initializes the Wrapper instance.
        __del__(self): Destructor method that calls the delete() method.
        delete(self): Deletes the wrapper instance.
        _open_stream_channel(self, **kwargs): Opens a stream channel for data streaming.
        getBalance(self): Retrieves the balance data.
        getCandles(self, symbol: str): Retrieves the candle data for a specific symbol.
        getNews(self): Retrieves the news data.
        getProfits(self): Retrieves the profits data.
        getTickPrices(self, symbol: str, minArrivalTime: int, maxLevel: int=1): Retrieves the tick prices data.
        getTrades(self): Retrieves the trades data.
        getTradeStatus(self): Retrieves the trade status data.
        _open_data_channel(self, **kwargs): Opens a data channel for data retrieval.
        getAllSymbols(self): Retrieves all symbols data.
        getCalendar(self): Retrieves the calendar data.
        getChartLastRequest(self, symbol: str, period: str, start: datetime=None): Retrieves the last chart data request.
        getChartRangeRequest(self, symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0): Retrieves the chart data within a range.
        getCommissionDef(self, symbol: str, volume: float): Retrieves the commission definition data.
        getCurrentUserData(self): Retrieves the current user data.
        getIbsHistory(self, start: datetime, end: datetime): Retrieves the IBS history data.
        getMarginLevel(self): Retrieves the margin level data.
        getMarginTrade(self, symbol: str, volume: float): Retrieves the margin trade data.
        getNews(self): Retrieves the news data.
        getProfitCalculation(self, symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int): Retrieves the profit calculation data.
        getServerTime(self): Retrieves the server time data.
        getStepRules(self): Retrieves the step rules data.
    """

    def __init__(self, demo: bool=True, logger=None):
        """
        Initializes the wrapper object.

        Args:
            demo (bool, optional): Specifies whether to use the demo mode. Defaults to True.
            logger (logging.Logger, optional): The logger object to use for logging. 
                If not provided, a new logger will be created. Defaults to None.
        """
        self._demo=demo

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger.getChild('Wrp')
        else:
            self._logger=generate_logger(name='Wrp', path=os.path.join(os.getcwd(), "logs"))

        self._logger.info("Initializing wrapper")

        self._utc_tz = pytz.utc
        self._cest_tz = pytz.timezone('Europe/Berlin')

        super().__init__(demo=self._demo, logger = self._logger)

        self._deleted=False

        self._logger.info("Wrapper initialized")

    def __del__(self):
        """
        Destructor method for the XTB wrapper class.
        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.
        """
        self.delete()

    def delete(self):
        """
        Deletes the wrapper.

        If the wrapper has already been deleted, a warning message is logged and the method returns True.

        Returns:
            bool: True if the wrapper is successfully deleted, False otherwise.
        """
        if self._deleted:
            self._logger.warning("Wrapper already deleted.")
            return True

        self._logger.info("Deleting wrapper.")
        super().delete()
        self._logger.info("Wrapper deleted.")

    def _open_stream_channel(self, **kwargs):
        """
        Opens a stream channel for receiving data.

        Args:
            **kwargs: Additional keyword arguments to be passed to the `streamData` method.

        Returns:
            Tuple: A tuple containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for thread synchronization.
                - thread (Thread): Startin the Thread will terminate the stream

        Raises:
            None

        """
        sh = self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide stream channel")
            return False
        
        df = pd.DataFrame()
        lock = Lock()

        thread = sh.streamData(df=df, lock=lock, **kwargs)

        return df, lock, thread
    
    def getBalance(self):
        """
        Allows to get actual account indicators values in real-time, as soon as they are available in the system.

        Returns:
            The balance of the trading account.
        
        Format of Output:
            name	            type	    description
            balance	            float	    balance in account currency
            credit	            float	    credit in account currency
            equity	            float	    sum of balance and all profits in account currency
            margin	            float	    margin requirements
            marginFree	        float	    free margin
            marginLevel	        float	    margin level percentage

        """
        return self._open_stream_channel(command="Balance")

    def getCandles(self, symbol: str):
        """
        Subscribes for and unsubscribes from API chart candles. The interval of every candle is 1 minute. A new candle arrives every minute

        Parameters:
        symbol (str): The symbol for which to retrieve the candles.

        Returns:
            The candles for the specified symbol.
        
        Format of Output:
            name	            type	    description
            close	            float	    Close price in base currency
            ctm	                timestamp	Candle  start time in CET time zone (Central European Time)
            ctmString	        string	    String representation of the ctm field
            high	            float	    Highest value in the given period in base currency
            low	                float	    Lowest  value in the given period in base currency
            open	            float	    Open price in base currency
            quoteId	            int	        Source of price
            symbol	            string	    Symbol
            vol	                float	    Volume in lots

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        """
        return self._open_stream_channel(command="Candles", symbol=symbol)
    
    def getNews(self):
        """
        Subscribes for and unsubscribes from news.

        Returns:
            The news data retrieved from the API.
        
        Format of Output:
            name	            type	    description
            body	            string	    Body
            key	                string	    News key
            time	            timestamp	Time
            title	            string	    News title
        """
        return self._open_stream_channel(command="News")

    def getProfits(self):
        """
        Subscribes for and unsubscribes from profits.

        Returns:
            The profits from the XTB trading platform.

        Format of Output:
            name	            type	    description
            order	            int	    Order number
            order2	            int	    Transaction ID
            position	        int	    Position number
            profit	            float	Profit in account currency

        """
        return self._open_stream_channel(command="Profits")

    def getTickPrices(self, symbol: str, minArrivalTime: int, maxLevel: int=1):
        """
        Establishes subscription for quotations and allows to obtain the relevant information in real-time, as soon as it is available in the system.

        Args:
            symbol (str): The symbol for which to retrieve tick prices.
            minArrivalTime (int): The minimum arrival time for the tick prices.
            maxLevel (int, optional): The maximum level of tick prices to retrieve. Defaults to 1.

        Returns:
            The tick prices for the specified symbol within the specified time range.

        Format of Output:
            name	            type	    description
            ask	                float	    Ask price in base currency
            askVolume	        int	        Number of available lots to buy at given price or null if not applicable
            bid	                float	    Bid price in base currency
            bidVolume	        int	        Number of available lots to buy at given price or null if not applicable
            high	            float	    The highest price of the day in base currency
            level	            int	        Price level
            low	                float	    The lowest price of the day in base currency
            quoteId	            int	        Source of price, detailed description below
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            symbol	            string	    Symbol
            timestamp	        timestamp	Timestamp

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        """
        if minArrivalTime < SEND_INTERVAL:
            minArrivalTime=SEND_INTERVAL
            self._logger.warning("minArrivalTime must be greater than " + str(SEND_INTERVAL) + ". Setting minArrivalTime to " + str(SEND_INTERVAL))

        if maxLevel < 1:
            maxLevel=1
            self._logger.warning("maxLevel must be greater than 1. Setting maxLevel to 1")

        return self._open_stream_channel(command="TickPrices", symbol=symbol, minArrivalTime=minArrivalTime, maxLevel=maxLevel)

    def getTrades(self):
        """
        Establishes subscription for user trade status data and allows to obtain the relevant information in real-time, as soon as it is available in the system.
        New  are sent by streaming socket only in several cases:
            - Opening the trade
            - Closing the trade
            - Modification of trade parameters
            - Explicit trade update done by server system to synchronize data.

        Returns:
            The trades retrieved from the XTB API.

        Format of Output:
            name	            type	    description
            close_price	        float	    Close price in base currency
            close_time	        timestamp	Null if order is not closed
            closed	            boolean	    Closed
            cmd	                int	        Operation code
            comment	            string	    Comment
            commission	        float	    Commission in account currency, null if not applicable
            customComment	    string	    The value the customer may provide in order to retrieve it later.
            digits	            int	        Number of decimal places
            expiration	        timestamp	Null if order is not closed
            margin_rate	        float	    Margin rate
            offset	            int	        Trailing offset
            open_price	        float	    Open price in base currency
            open_time	        timestamp	Open time
            order	            int	        Order number for opened transaction
            order2	            int	        Transaction id
            position	        int	        Position number (if type is 0 and 2) or transaction parameter (if type is 1)
            profit	            float	    null unless the trade is closed (type=2) or opened (type=0)
            sl	                float	    Zero if stop loss is not set (in base currency)
            state	            string	    Trade state, should be used for detecting pending order's cancellation
            storage	            float	    Storage
            symbol	            string	    Symbol
            tp	                float	    Zero if take profit is not set (in base currency)
            type	            int	        type
            volume	            float	    Volume in lots

        Possible values of cmd field:
            name	            value	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        Possible values of comment field:
            - "[S/L]", then the trade was closed by stop loss
            - "[T/P]", then the trade was closed by take profit
            - "[S/O margin level% equity / margin (currency)]", then the trade was closed because of Stop Out
            - If the comment remained unchanged from that of opened order, then the order was closed by user

        Possible values of state field:
            name	            value	        description
            MODIFIED	        "Modified"	    modified
            DELETED	            "Deleted"	    deleted

        Possible values of type field:
            name	            value	        description
            OPEN	            0	            order open, used for opening orders
            PENDING	            1	            order pending, only used in the streaming getTrades  command
            CLOSE	            2	            order close
            MODIFY	            3	            order modify, only used in the tradeTransaction  command
            DELETE	            4	            order delete, only used in the tradeTransaction  command

        
        """
        return self._open_stream_channel(command="Trades")
    
    def getTradeStatus(self):
        """
            Allows to get status for sent trade requests in real-time, as soon as it is available in the system.

        Returns:
            The trade status.

        Format of Output:
            name	            type	    description
            customComment	    string	    The value the customer may provide in order to retrieve it later.
            message	            string	    Can be null
            order	            int	        Unique order number
            price	            float	    Price in base currency
            requestStatus	    int	        Request status code, described below

        """
        return self._open_stream_channel(command="TradeStatus")

    def _open_data_channel(self, **kwargs):
        """
        Opens a data channel and retrieves data using the provided DataHandler.

        Args:
            **kwargs: Additional keyword arguments to be passed to the getData method of the DataHandler.

        Returns:
            The response from the getData method if successful, False otherwise.
        """
        dh = self.provide_DataHandler()
        if not dh:
            self._logger("Could not provide data channel")
            return False
        
        response = dh.getData(**kwargs)

        if not response:
            return False
        else:
            return response
        
    def getAllSymbols(self):
        """
        Retrieves all symbols from the data channel.

        Returns:
            A list of symbols available in the data channel.

        Format of Output:
            name	            type	    description
            ask	                float	    Ask price in base currency
            bid	                float	    Bid price in base currency
            categoryName	    String	    Category name
            contractSize	    Number	    Size of 1 lot
            currency	        String	    Currency
            currencyPair	    Boolean	    Indicates whether the symbol represents a currency pair
            currencyProfit	    String	    The currency of calculated profit
            description	        String	    Description
            expiration	        Time	    Null if not applicable
            groupName	        String	    Symbol group name
            high	            float	    The highest price of the day in base currency
            initialMargin	    Number	    Initial margin for 1 lot order, used for profit/margin calculation
            instantMaxVolume    Number	    Maximum instant volume multiplied by 100 (in lots)
            leverage	        float	    Symbol leverage
            longOnly	        Boolean	    Long only
            lotMax	            float	    Maximum size of trade
            lotMin	            float	    Minimum size of trade
            lotStep	            float	    A value of minimum step by which the size of trade can be changed (within lotMin - lotMax range)
            low	                float	    The lowest price of the day in base currency
            marginHedged	    Number	    Used for profit calculation
            marginHedgedStrong  Boolean	    For margin calculation
            marginMaintenance   Number	    For margin calculation, null if not applicable
            marginMode	        Number	    For margin calculation
            percentage	        float	    Percentage
            pipsPrecision	    Number	    Number of symbol's pip decimal places
            precision	        Number	    Number of symbol's price decimal places
            profitMode	        Number	    For profit calculation
            quoteId     	    Number	    Source of price
            shortSelling	    Boolean	    Indicates whether short selling is allowed on the instrument
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            starting	        Time	    Null if not applicable
            stepRuleId	        Number	    Appropriate step rule ID from getStepRules  command response
            stopsLevel	        Number	    Minimal distance (in pips) from the current price where the stopLoss/takeProfit can be set
            swap_rollover3days	Number	    Time when additional swap is accounted for weekend
            swapEnable	        Boolean	    Indicates whether swap value is added to position on end of day
            swapLong	        float	    Swap value for long positions in pips
            swapShort	        float	    Swap value for short positions in pips
            swapType	        Number	    Type of swap calculated
            symbol	            String	    Symbol name
            tickSize	        float	    Smallest possible price change, used for profit/margin calculation, null if not applicable
            tickValue	        float	    Value of smallest possible price change (in base currency), used for profit/margin calculation, null if not applicable
            time	            Time	    Ask & bid tick time
            timeString	        String	    Time in String
            trailingEnabled	    Boolean 	Indicates whether trailing stop (offset) is applicable to the instrument.
            type	            Number	    Instrument class number

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        Possible values of marginMode field:
            name	            value	    description
            Forex	            101	        Forex
            CFD leveraged	    102	        CFD leveraged
            CFD	                103	        CFD

        Possible values of profitMode field:
            name	            value	    description
            FOREX	            5	        FOREX
            CFD	                6	        CFD

        """
        return self._open_data_channel(command="AllSymbols")
    
    def getCalendar(self):
            """
            Retrieves the calendar data from the XTB API.

            Returns:
                The calendar data as returned by the XTB API.

            """
            return self._open_data_channel(command="Calendar")
    
    def getChartLastRequest(self, symbol: str, period: str, start: datetime=None):
        periods=[
            "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"
        ]

        if period not in periods:
            self._logger("Invalid period. Choose from: "+", ".join(periods))
            return False
        
        now=datetime.datetime.now()
        now_time = now.timestamp()
        if period in periods[6:]:
            time_limit=None
        elif period in periods[5:]:
            time_limit=now - relativedelta(years=13)
        elif period in periods[3:]:
            time_limit=now - relativedelta(months=7)
        else:
            time_limit=now - relativedelta(months=1)
        time_limit=time_limit.timestamp()
        
        if not start:
            start_time=datetime.min().timestamp()
        else:
            start_time=start.timestamp()

        if start_time > now_time:
            self._logger.error("Start time is greater than current time.")
            return False

        if start_time < time_limit:
            self._logger.warning("Start time is too far in the past for selected period "+period+". Setting start time to "+str(time_limit))
            start_time=time_limit

        return self._open_data_channel(command="ChartLastRequest", period=period, start=start_time, symbol=symbol)

    def getChartRangeRequest(self, symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0):
        periods=[
            "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"
        ]

        if period not in periods:
            self._logger("Invalid period. Choose from: "+", ".join(periods))
            return False
        
        now=datetime.datetime.now()
        now_time = now.timestamp()
        if period in periods[6:]:
            time_limit=None
        elif period in periods[5:]:
            time_limit=now - relativedelta(years=13)
        elif period in periods[3:]:
            time_limit=now - relativedelta(months=7)
        else:
            time_limit=now - relativedelta(months=1)
        time_limit=time_limit.timestamp()

        if not start:
            start_time=datetime.min().timestamp()
        else:
            start_time=start.timestamp()

        if start_time < time_limit:
            self._logger.warning("Start time is too far in the past for selected period "+period+". Setting start time to "+str(time_limit))
            start_time=time_limit

        if start_time > now_time:
            self._logger.error("Start time is greater than current time.")
            return False

        if ticks == 0:
            if not end:
                end_time=now_time
            else:
                end_time=end.timestamp()  
                
            if end_time > now_time:
                self._logger.error("End time is greater than current time.")
                return False

            if start_time >= end_time:
                self._logger.error("Start time is greater or equal than end time.")
                return False
        else:
            self._logger.info("Ticks parameter is set. Ignoring end time.")

            reference_time = start_time

            if ticks < 0:
                if period in ["M1", "M5", "M15", "M30"]:
                    delta = calculate_timedelta(time_limit,reference_time, period='minutes')
                elif period in ["H1", "H4"]:
                    delta = calculate_timedelta(time_limit,reference_time, period='hours')
                elif period is "D1":
                    delta = calculate_timedelta(time_limit,reference_time, period='days')
                elif period is "W1":
                    delta = calculate_timedelta(time_limit,reference_time, period='weeks')
                else:
                    delta = calculate_timedelta(reference_time, now_time,period='months')

                if delta < abs(ticks):
                    self._logger.warning("Ticks reach too far in the past for selected period "+period+". Setting tick to "+str(delta))
                    ticks = delta
            else:
                if period in ["M1", "M5", "M15", "M30"]:
                    delta = calculate_timedelta(reference_time, now_time, period='minutes')
                elif period in ["H1", "H4"]:
                    delta = calculate_timedelta(reference_time, now_time, period='hours')
                elif period is "D1":
                    delta = calculate_timedelta(reference_time, now_time, period='days')
                elif period is "W1":
                    delta = calculate_timedelta(reference_time, now_time, period='weeks')
                else:
                    delta = calculate_timedelta(reference_time, now_time, period='months')
                
                if delta < ticks:
                    self._logger.warning("Ticks reach too far in the future for selected period "+period+". Setting tick time to "+str(delta))
                    ticks = delta

        return self._open_data_channel(command="ChartRangeRequest", end=end_time, period=period, start=start_time, symbol=symbol, ticks=ticks)

    def getCommissionDef(self, symbol: str, volume: float):
        return self._open_data_channel(command="CommissionDef", symbol=symbol, volume=volume)
    
    def getCurrentUserData(self):
        return self._open_data_channel(command="CurrentUserData")
    
    def getIbsHistory(self, start: datetime, end: datetime):
        start_time=start.timestamp()
        end_time=end.timestamp()

        return self._open_data_channel(command="IbsHistory", start=start_time, end=end_time)
    
    def getMarginLevel(self):
        return self._open_data_channel(command="MarginLevel")
    
    def getMarginTrade(self, symbol: str, volume: float):
        return self._open_data_channel(command="MarginTrade", symbol=symbol, volume=volume)
    
    def getNews(self):
        return self._open_data_channel(command="News")
    
    def getProfitCalculation(self, symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int):
        cmds = [0, 1, 2, 3, 4, 5, 6, 7]

        if cmd not in cmds:
            self._logger.error("Invalid cmd. Choose from: "+", ".join(cmds))
            return False

        return self._open_data_channel(command="ProfitCalculation", closePrice=closePrice, cmd=cmd, openPrice=openPrice, symbol=symbol, volume=volume)
        
    def getServerTime(self):
        return self._open_data_channel(command="ServerTime")
    
    def getStepRules(self):
        return self._open_data_channel(command="StepRules")

    def getSymbol(self, symbol: str):
        return self._open_data_channel(command="Symbol")
    
    def getTickPrices(self, symbols: list, time: datetime, level: int=-1):
        levels = [-1, 0]

        if level not in levels or level > 0:
            self._logger.error("Invalid level. Choose from: "+", ".join(levels))
            return False
        
        if all(isinstance(item, str) for item in levels):
            self._logger.error("Invalid symbols. All symbols must be strings.")
            return False
        
        timestamp=time.timestamp()

        return self._open_data_channel(command="TickPrices", symbols=symbols, timestamp=timestamp)
    
    def getTradeRecords(self, orders: list):

        if all(isinstance(item, int) for item in orders):
            self._logger.error("Invalid order. All orders must be integers.")
            return False

        return self._open_data_channel(command="TradeRecords", orders=orders)
    
    def getTrades(self, openedOnly: bool):
        return self._open_data_channel(command="Trades", openedOnly=openedOnly)
    
    def getTradeHistory(self, start: datetime, end: datetime):
        if end == 0:
            end = datetime.datetime.now()

        if start == 0:
            start = end - relativedelta(months=1)

        start_time=start.timestamp()
        end_time=end.timestamp()

        return self._open_data_channel(command="TradeHistory", start=start_time, end=end_time)
    
    def getTradingHours(self, symbols: list):
        if all(isinstance(item, str) for item in symbols):
            self._logger.error("Invalid symbols. All symbols must be strings.")
            return False

        return self._open_data_channel(command="TradingHours", symbols=symbols)

    def getVersion(self):
        return self._open_data_channel(command="Version")
    
    def tradeTransaction(self, cmd: int, symbol: str, volume: float, openPrice: float, sl: float, tp: float, comment: str):
        cmds = [0, 1, 2, 3, 4, 5, 6, 7]

        if cmd not in cmds:
            self._logger.error("Invalid cmd. Choose from: "+", ".join(cmds))
            return False

        return self._open_data_channel(command="TradeTransaction", cmd=cmd, symbol=symbol, volume=volume, openPrice=openPrice, sl=sl, tp=tp, comment=comment)
    
    def tradeTransactionStatus(self, order: int):
        return self._open_data_channel(command="TradeTransactionStatus", order=order)









    