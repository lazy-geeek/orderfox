## FEATURE:

Okay, here comes another feature request change. We currently have the liquidation data stream in the backend. 
The problem is that we only receive new liquidations if we restart the server or change the symbol. 
But there is an API we can call to get historical liquidation orders. 
So we can call the historical orders and mix them with the newly incoming liquidation orders. 
Please see the documentation below how we can receive the liquidation orders from the API. 
Please implement this for the backend and use the same technique as before. 
So that with the first WebSocket tick, we are sending the historical data and the following ticks are sending the received current liquidation orders.
Please fetch the last 50 liquidation orders from the API and keep this as a fixed list of 50. So if new liquidation orders are coming in, then remove the last ones from the list. 
You need to calculate the USDT value yourself by the same multiplication as in the live liquidation order stream, so that we have the same values. 

Please add a new variable the to backend .env file where i will set the base url for the liquidation API.


## DOCUMENTATION:

https://github.com/lazy-geeek/liqui_api







