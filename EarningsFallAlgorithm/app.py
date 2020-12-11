class EarningsFall(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 12, 1)  # Set Start Date
        self.SetEndDate(2020, 12, 1)
        self.SetCash(100000)  # Set Strategy Cash
        
        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddUniverse(self.CoarseSelection, self.FineSelection)
        
        self.longSymbols = []
        self.entryPrices = {}
        self.highestPrice = {}
        self.stopMarketTicket = {}
        
        stockPlot = Chart("Positions")
        stockPlot.AddSeries(Series("Longs", SeriesType.Bar, 0))
        self.AddChart(stockPlot)
        
        self.AddEquity("SPY", Resolution.Daily) #Add SPY as benchmark
        self.SetBenchmark("SPY")
        
        self.Schedule.On(self.DateRules.EveryDay("SPY"), self.TimeRules.At(10, 00), self.EveryMarketOpen) #set to run at 10 AM everyday that SPY trades
        
        self.entryMove = 0.02 #Minumum percentage fall to buy stock
        self.maxPositions = 10 #Maximum positions to buy in stock
        self.numOfCoarse = 6 * self.maxPositions
        self.daysSinceEarnings = 1
        self.stopLoss = .1
        
    def CoarseSelection(self, coarse):
        selectedByDollarVolume = sorted([x for x in coarse if x.Price > 5 and x.HasFundamentalData],
                                        key = lambda x: x.DollarVolume, reverse = True) #Look through all stocks that are above $5 and have fundamental date, sorted by Dollars
        return [x.Symbol for x in selectedByDollarVolume[:self.numOfCoarse]]
        
    def FineSelection(self, fine):
        fine = [x for x in fine if self.Time == x.EarningReports.FileDate + timedelta(days=self.daysSinceEarnings)]
        symbols = [x.Symbol for x in fine]
        pricesAroundEarnings = self.History(symbols, self.daysSinceEarnings+3, Resolution.Daily)
        
        for sec in fine:
            date = min(pricesAroundEarnings.loc[sec.Symbol]["close"].index,
                        key = lambda x: abs(x-(sec.EarningReports.FileDate - timedelta(1))))
            priceOnEarnings = pricesAroundEarnings.loc[sec.Symbol]["close"][date]
            if priceOnEarnings * (1-self.entryMove) > sec.Price:
                self.longSymbols.append(sec.Symbol)
        return self.longSymbols
        
    def EveryMarketOpen(self):
        positions = [sec.Symbol for sec in self.Portfolio.Values if self.Portfolio[sec.Symbol].Invested]
        self.Plot("Positions", "Longs", len(positions))
        availableTrades = self.maxPositions - len(positions)
        
        for symbol in [x for x in self.longSymbols if x not in positions][:availableTrades]:
            if self.Securities.ContainsKey(symbol):
                self.SetHoldings(symbol, 1 / self.maxPositions)
                
        self.longSymbols = []
        
        for symbol in positions:
            if not self.Transactions.GetOpenOrders(symbol):
                self.stopMarketTicket[symbol] = self.StopMarketOrder(symbol, -self.Portfolio[symbol].Quantity, (1-self.stopLoss)*self.entryPrices[symbol])
            elif self.Securities[symbol].Close > self.highestPrice[symbol]:
                self.highestPrice[symbol] = self.Securities[symbol].Close
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[symbol].Close * (1-self.stopLoss)
                self.stopMarketTicket[symbol].Update(updateFields)
    
    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.entryPrices[orderEvent.Symbol] = orderEvent.FillPrice
            self.highestPrice[orderEvent.Symbol] = orderEvent.FillPrice