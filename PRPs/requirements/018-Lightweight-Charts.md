## FEATURE:

The frontend is currently using Apache ECharts for the display of the candlestick charts. This is generally working but however, i want to switch to tradingview's lightweight-charts library. This type of chart is more commonly used in the crypto space and has a more modern look and feel. It also has better performance for large datasets.
Please replace the current ECharts implementation with the lightweight-charts library and preserve the existing functionality of the candlestick charts. Also consider the dark mode implementation, which should be preserved as well. the switching of the symbols and timeframes must also be preserved and the chart must react to those changes.
Remember to have the backend handle all the data and preprocessing, so the frontend only needs to render the data.
Maybe we can do the same optimizations as we did for the orderbook, where the backend sends the historical data with the first websocket message and the real time updates with the following websocket messages. please check if this can be optimized in the backend to reduce the communication overhead.

## DOCUMENTATION:

[Link to the lightweight-charts documentation](https://tradingview.github.io/lightweight-charts/)
You may also use the context7 mcp server to refer to the documentation for the lightweight-charts library in a llm friendly way.

For legacy, here is the [ECharts documentation](https://echarts.apache.org/en/index.html) for reference.
You may also use the context7 mcp server to refer to the documentation for the echarts library in a llm friendly way.



