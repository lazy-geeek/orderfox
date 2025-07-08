## FEATURE:

In the frontend I want to add a table element below the orderbook that shows the last trades for the selected symbol.
See screenshot below from Binance for an example of how it should look like. Ignore the "Top Movers" tab.
/mnt/c/Users/Bail/AppData/Local/Temp/2/img_20250708_131319.png    

The table should be updated in real-time with the latest trades for the selected symbol. I guess we need the watchTrades method from the ccxt.pro library for this.

The columns should match the alignment of the above orderbook columns. Also use the price precision for the symbol. Color the price and amount columns green for buys and red for sells. The table should be scrollable if there are too many trades to fit in the view. Only keep the last 100 trades in the list. When more trades are coming in, cut the list at the end so that we always have 100. To fill up the trades in the list when reloading the page or selecting another symbol, I think we need to use the CCXT module to fetch the last trades and then mix it with the incoming new trades from the CCXT Pro real-time websocket. As already implemented for the chart and the orderbook, this data must all be prepared by the back-end and only populated via WebSocket to the front-end. And we should also have the same technique that when the first tick is sent to the WebSocket for the last trades, This first tick is containing the last 100 historical trades, and for the next ticks, it is updated with the incoming real-time trades. 

The new table element should use the same coloring as the orderbook and also respond to the dark mode switching. 

Here is how the orderbook and last trades table should look like together:
mnt/c/Users/Bail/AppData/Local/Temp/2/img_20250708_132649.png

## DOCUMENTATION:

CCXT Pro library documentation: https://docs.ccxt.com/#/ccxt.pro.manual
CCXT library documentation: https://docs.ccxt.com/#/
You may also use the context7 mcp server to refer to the documentation for the CCXT and CCXT Pro library in a llm friendly way.





