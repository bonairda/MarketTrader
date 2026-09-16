"""Tests de los mapeadores de CSV de brokers."""

import pytest

from app.core.errors import AppError
from app.modules.operations import brokers


def test_generic_maps_buy_and_sell_with_stable_ids():
    csv = (
        "assetId;side;tradeDate;quantity;unitPriceOriginal;grossAmountOriginal;currency;externalId\n"
        "stock:AAPL;BUY;2025-01-02;10;100;1000;USD;A1\n"
        "btcusdt;SELL;2025-02-03;0,5;30000;15000;EUR;B2\n"
    )
    rows = brokers.map_broker_csv("generic", csv)
    assert rows[0]["assetId"] == "stock:AAPL"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["fxSource"] == "ECB"  # USD -> lo resuelve el backend
    assert rows[1]["quantity"] == "0.5"  # coma decimal normalizada
    assert rows[1]["fxSource"] == "USER"  # EUR
    assert rows[1]["fxRateToEur"] == "1"
    # externalId determinista: mismo CSV -> mismos ids
    again = brokers.map_broker_csv("generic", csv)
    assert [r["externalId"] for r in rows] == [r["externalId"] for r in again]


def test_trade_republic_prefixes_isin_as_stock():
    csv = (
        "Date;Type;ISIN;Shares;Price;Amount;Currency;ID\n"
        "2025-03-10T10:00:00;Buy;US0378331005;5;180;900;EUR;TR1\n"
        "2025-03-10;Dividend;US0378331005;;;3.5;EUR;TR2\n"
    )
    rows = brokers.map_broker_csv("trade_republic", csv)
    # El dividendo se ignora aquí (se registra como evento corporativo aparte).
    assert len(rows) == 1
    assert rows[0]["assetId"] == "stock:US0378331005"
    assert rows[0]["tradeDate"] == "2025-03-10"


def test_revolut_uses_usd_by_default():
    csv = (
        "Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency\n"
        "2025-04-01,TSLA,BUY,2,200,400,USD\n"
    )
    rows = brokers.map_broker_csv("revolut", csv)
    assert rows[0]["assetId"] == "stock:TSLA"
    assert rows[0]["currency"] == "USD"
    assert rows[0]["fxSource"] == "ECB"


def test_unsupported_broker_raises():
    with pytest.raises(AppError) as exc:
        brokers.map_broker_csv("desconocido", "a,b\n1,2\n")
    assert exc.value.code == "UNSUPPORTED_BROKER"


def test_no_operations_found_raises():
    csv = "Date;Type;ISIN\n2025-01-01;Dividend;US0378331005\n"
    with pytest.raises(AppError) as exc:
        brokers.map_broker_csv("trade_republic", csv)
    assert exc.value.code == "NO_OPERATIONS_FOUND"
