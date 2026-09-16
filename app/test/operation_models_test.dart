import 'package:flutter_test/flutter_test.dart';
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
}
