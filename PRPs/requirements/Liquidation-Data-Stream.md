## FEATURE:

I want to add another data stream to the app. It's about the liquidation orders from Binance. Unfortunately, this is not offered by CCXT Pro, so we need to establish the connection directly to the Binance API. 
To show them on the front end, add another container table right to the trades Below the chart. The new table must be styled as the existing orderbook and trades tables containers. 
The table should show the incoming liquidation orders for the selected symbol. It should show the following columns:
- Side (Buy/Sell)
- Quantity
- Price in USDT (Order Filled Accumulated Quantity * Price)

As always, the data must be retrieved from the backend and then only sent to the frontend without doing any functionality on the frontend, which is only the receiving and displaying part. 


## DOCUMENTATION:

Link to the Bincance Liquidation Data Stream documentation: https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Liquidation-Order-Streams
Link to the Bincance Futures documentation: https://developers.binance.com/docs/derivatives/usds-margined-futures/
Also use the context7 mcp server to get the documentations.





