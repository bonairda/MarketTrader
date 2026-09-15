import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:market_tracker/models/price_bar.dart';
import 'package:market_tracker/widgets/candlestick_chart.dart';

void main() {
  // Smoke test de un widget puro (sin red ni timers): el gráfico de velas se
  // renderiza sin lanzar excepciones con un conjunto de datos válido.
  testWidgets('CandlestickChart se renderiza con velas', (WidgetTester tester) async {
    final bars = [
      PriceBar(
        openTime: DateTime.utc(2025, 1, 1, 0, 0),
        open: 10,
        high: 12,
        low: 9,
        close: 11,
      ),
      PriceBar(
        openTime: DateTime.utc(2025, 1, 1, 0, 1),
        open: 11,
        high: 14,
        low: 10,
        close: 13,
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: CandlestickChart(bars: bars)),
      ),
    );

    expect(find.byType(CandlestickChart), findsOneWidget);
  });
}
