import 'package:flutter_test/flutter_test.dart';
import 'package:market_tracker/models/derived_portfolio.dart';
import 'package:market_tracker/models/operation.dart';
import 'package:market_tracker/models/tax_report.dart';

void main() {
  test('InvestmentOperation conserva decimales como texto', () {
    final operation = InvestmentOperation.fromJson({
      'id': 'op-1',
      'assetId': 'stock:AAPL',
      'side': 'BUY',
      'tradeDate': '2025-01-01',
      'executedAt': null,
      'quantity': '0.123456789012',
      'unitPriceOriginal': '100.000000000000',
      'grossAmountOriginal': '12.345678901200',
      'feesOriginal': '1.000000000000',
      'currency': 'USD',
      'fxRateToEur': '0.920000000000',
      'grossAmountEur': '11.36',
      'feesEur': '0.92',
      'cashAmountEur': '12.28',
      'fxSource': 'ECB',
      'source': 'MANUAL',
      'externalId': null,
      'notes': null,
    });
    expect(operation.quantity, '0.123456789012');
    expect(operation.isBuy, isTrue);
    expect(operation.fxRateToEur, '0.920000000000');
  });

  test('NewInvestmentOperation genera el contrato esperado', () {
    const input = NewInvestmentOperation(
      assetId: 'stock:AAPL',
      side: 'SELL',
      tradeDate: '2025-02-01',
      quantity: '2',
      unitPriceOriginal: '120',
      grossAmountOriginal: '240',
      feesOriginal: '1',
      currency: 'USD',
      fxRateToEur: '0.9',
    );
    expect(input.toJson()['side'], 'SELL');
    expect(input.toJson()['fxSource'], 'USER');
    expect(input.toJson().containsKey('notes'), isFalse);
  });

  test('TaxReport parsea resumen y emparejamientos', () {
    final report = TaxReport.fromJson({
      'year': 2025,
      'currency': 'EUR',
      'summary': {
        'sellOperations': 1,
        'matchedLots': 1,
        'proceedsEur': '120.00',
        'acquisitionCostEur': '100.00',
        'feesEur': '2.00',
        'realizedGainEur': '20.00',
      },
      'assets': [
        {
          'assetId': 'stock:AAPL',
          'quantitySold': '1.000000000000',
          'proceedsEur': '120.00',
          'acquisitionCostEur': '100.00',
          'feesEur': '2.00',
          'realizedGainEur': '20.00',
        }
      ],
      'disposals': [
        {
          'assetId': 'stock:AAPL',
          'sellOperationId': 's1',
          'saleDate': '2025-02-01',
          'buyOperationId': 'b1',
          'acquisitionDate': '2024-01-01',
          'matchedQuantity': '1.000000000000',
          'proceedsEur': '120.00',
          'acquisitionCostEur': '100.00',
          'gainEur': '20.00',
        }
      ],
      'openLots': [],
      'disclaimer': 'Borrador',
    });
    expect(report.summary.realizedGainEur, '20.00');
    expect(report.assets.single.assetId, 'stock:AAPL');
    expect(report.disposals.single.buyOperationId, 'b1');
  });

  test('NewInvestmentOperation omite fxRateToEur cuando es null (auto ECB)', () {
    const auto = NewInvestmentOperation(
      assetId: 'stock:AAPL',
      side: 'BUY',
      tradeDate: '2025-01-01',
      quantity: '1',
      unitPriceOriginal: '100',
      grossAmountOriginal: '100',
      feesOriginal: '0',
      currency: 'USD',
      fxSource: 'ECB',
    );
    expect(auto.toJson().containsKey('fxRateToEur'), isFalse);
    expect(auto.toJson()['fxSource'], 'ECB');
  });

  test('OperationPage parsea metadatos de paginación', () {
    final page = OperationPage.fromJson({
      'items': [],
      'total': 130,
      'limit': 50,
      'offset': 50,
      'hasMore': true,
      'nextOffset': 100,
    });
    expect(page.total, 130);
    expect(page.hasMore, isTrue);
    expect(page.nextOffset, 100);
  });

  test('ImportResult parsea el resumen', () {
    final result = ImportResult.fromJson({
      'dryRun': true,
      'received': 5,
      'created': 3,
      'skipped': 1,
      'failed': 1,
    });
    expect(result.dryRun, isTrue);
    expect(result.created, 3);
  });

  test('DerivedPortfolio parsea posiciones y resumen', () {
    final portfolio = DerivedPortfolio.fromJson({
      'positions': [
        {
          'assetId': 'stock:AAPL',
          'quantity': '5.000000000000',
          'avgCostEur': '90.00',
          'costEur': '450.00',
          'priceEur': '100.00',
          'marketValueEur': '500.00',
          'pnlEur': '50.00',
          'pnlPercent': '11.11',
        }
      ],
      'summary': {
        'totalCostEur': '450.00',
        'totalValueEur': '500.00',
        'totalPnlEur': '50.00',
        'totalPnlPercent': '11.11',
        'positions': 1,
      },
      'note': 'derivada',
    });
    expect(portfolio.positions.single.assetId, 'stock:AAPL');
    expect(portfolio.totalPnlEur, '50.00');
  });

  test('TaxDisposal parsea la marca de recompra homogénea', () {
    final disposal = TaxDisposal.fromJson({
      'assetId': 'stock:AAPL',
      'sellOperationId': 's1',
      'saleDate': '2025-02-01',
      'buyOperationId': 'b1',
      'acquisitionDate': '2025-01-01',
      'matchedQuantity': '10',
      'proceedsEur': '800.00',
      'acquisitionCostEur': '1000.00',
      'gainEur': '-200.00',
      'washSale': true,
      'washSaleReason': 'Posible recompra',
    });
    expect(disposal.washSale, isTrue);
    expect(disposal.washSaleReason, 'Posible recompra');
  });
}
