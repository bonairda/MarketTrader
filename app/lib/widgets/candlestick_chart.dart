import 'package:flutter/material.dart';

import '../models/price_bar.dart';

/// Gráfico de velas básico dibujado con CustomPainter (sin dependencias).
class CandlestickChart extends StatelessWidget {
  const CandlestickChart({super.key, required this.bars});

  final List<PriceBar> bars;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return CustomPaint(
          size: Size(constraints.maxWidth, constraints.maxHeight),
          painter: _CandlePainter(bars),
        );
      },
    );
  }
}

class _CandlePainter extends CustomPainter {
  _CandlePainter(this.bars);

  final List<PriceBar> bars;

  static const _up = Color(0xFF26A69A);
  static const _down = Color(0xFFEF5350);

  @override
  void paint(Canvas canvas, Size size) {
    if (bars.isEmpty) return;

    double minLow = bars.first.low;
    double maxHigh = bars.first.high;
    for (final b in bars) {
      if (b.low < minLow) minLow = b.low;
      if (b.high > maxHigh) maxHigh = b.high;
    }
    final range = (maxHigh - minLow).abs();
    final safeRange = range == 0 ? 1.0 : range;

    double yFor(double price) =>
        size.height - ((price - minLow) / safeRange) * size.height;

    final slot = size.width / bars.length;
    final bodyWidth = (slot * 0.6).clamp(1.0, 12.0);

    for (var i = 0; i < bars.length; i++) {
      final b = bars[i];
      final cx = slot * i + slot / 2;
      final isUp = b.close >= b.open;
      final paint = Paint()
        ..color = isUp ? _up : _down
        ..strokeWidth = 1;

      // Mecha (high-low)
      canvas.drawLine(Offset(cx, yFor(b.high)), Offset(cx, yFor(b.low)), paint);

      // Cuerpo (open-close)
      final top = yFor(isUp ? b.close : b.open);
      final bottom = yFor(isUp ? b.open : b.close);
      final rect = Rect.fromLTRB(
        cx - bodyWidth / 2,
        top,
        cx + bodyWidth / 2,
        bottom == top ? top + 1 : bottom,
      );
      canvas.drawRect(rect, paint..style = PaintingStyle.fill);
    }
  }

  @override
  bool shouldRepaint(covariant _CandlePainter oldDelegate) =>
      oldDelegate.bars != bars;
}
