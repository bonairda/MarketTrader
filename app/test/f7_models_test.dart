import 'package:flutter_test/flutter_test.dart';
import 'package:market_tracker/models/corporate_event.dart';
import 'package:market_tracker/models/paper_trading.dart';
import 'package:market_tracker/models/tax_report.dart';

void main() {
  test('CorporateEvent parsea un dividendo con importes EUR', () {
    final event = CorporateEvent.fromJson({
      'id': 'e1',
      'assetId': 'stock:AAPL',
      'type': 'DIVIDEND',
      'eventDate': '2025-03-01',
      'grossAmountOriginal': '100.000000000000',
      'withholdingOriginal': '15.000000000000',
      'currency': 'USD',
      'grossAmountEur': '90.00',
      'withholdingEur': '13.50',
      'netAmountEur': '76.50',
    });
    expect(event.isDividend, isTrue);
    expect(event.netAmountEur, '76.50');
  });

  test('NewCorporateEvent de split solo envía ratio', () {
    const split = NewCorporateEvent(
      assetId: 'stock:AAPL',
      type: 'SPLIT',
      eventDate: '2025-06-01',
      ratio: '2',
    );
    final json = split.toJson();
    expect(json['ratio'], '2');
    expect(json.containsKey('grossAmountOriginal'), isFalse);
  });

  test('PaperTradingStatus parsea el flag enabled', () {
    final status = PaperTradingStatus.fromJson({'enabled': true, 'mode': 'paper'});
    expect(status.enabled, isTrue);
    expect(status.mode, 'paper');
  });

  test('PaperOrder acepta claves de Alpaca (qty/submitted_at)', () {
    final order = PaperOrder.fromJson({
      'symbol': 'AAPL',
      'side': 'buy',
      'qty': '3',
      'status': 'accepted',
      'submitted_at': '2025-01-01T10:00:00Z',
    });
    expect(order.side, 'BUY');
    expect(order.quantity, '3');
    expect(order.submittedAt, '2025-01-01T10:00:00Z');
  });

  test('TaxReport parsea la sección de dividendos', () {
    final report = TaxReport.fromJson({
      'year': 2025,
      'currency': 'EUR',
      'summary': {
        'sellOperations': 0,
        'matchedLots': 0,
        'proceedsEur': '0.00',
        'acquisitionCostEur': '0.00',
        'feesEur': '0.00',
        'realizedGainEur': '0.00',
        'washSaleDisposals': 0,
        'washSaleAdjustmentEur': '0.00',
      },
      'assets': [],
      'disposals': [],
      'disclaimer': 'borrador',
      'dividends': {
        'count': 2,
        'grossEur': '140.00',
        'withholdingEur': '18.50',
        'netEur': '121.50',
      },
    });
    expect(report.dividends, isNotNull);
    expect(report.dividends!.count, 2);
    expect(report.dividends!.netEur, '121.50');
  });
}
