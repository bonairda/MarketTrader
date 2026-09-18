import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/price_bar.dart';

/// Gráfico de velas dibujado con CustomPainter (sin dependencias externas).
///
/// Es interactivo: al pasar el ratón (web/escritorio) o arrastrar el dedo
/// (móvil) por encima, muestra una línea guía y un recuadro con el precio
/// (OHLC) y la fecha de la vela bajo el cursor.
class CandlestickChart extends StatefulWidget {
  const CandlestickChart({super.key, required this.bars});

  final List<PriceBar> bars;

  @override
  State<CandlestickChart> createState() => _CandlestickChartState();
}

class _CandlestickChartState extends State<CandlestickChart> {
  /// Índice de la vela resaltada, o null si el cursor no está sobre el gráfico.
  int? _activeIndex;

  void _updateFromPosition(Offset localPosition, double width) {
    final bars = widget.bars;
    if (bars.isEmpty || width <= 0) return;
    final slot = width / bars.length;
    var index = (localPosition.dx / slot).floor();
    if (index < 0) index = 0;
    if (index > bars.length - 1) index = bars.length - 1;
    if (index != _activeIndex) {
      setState(() => _activeIndex = index);
    }
  }

  void _clear() {
    if (_activeIndex != null) {
      setState(() => _activeIndex = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        return MouseRegion(
          onHover: (e) => _updateFromPosition(e.localPosition, width),
          onExit: (_) => _clear(),
          child: GestureDetector(
            onTapDown: (e) => _updateFromPosition(e.localPosition, width),
            onHorizontalDragStart: (e) =>
                _updateFromPosition(e.localPosition, width),
            onHorizontalDragUpdate: (e) =>
                _updateFromPosition(e.localPosition, width),
            onHorizontalDragEnd: (_) => _clear(),
            child: CustomPaint(
              size: Size(width, constraints.maxHeight),
              painter: _CandlePainter(
                bars: widget.bars,
                activeIndex: _activeIndex,
                theme: Theme.of(context),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CandlePainter extends CustomPainter {
  _CandlePainter({
    required this.bars,
    required this.activeIndex,
    required this.theme,
  });

  final List<PriceBar> bars;
  final int? activeIndex;
  final ThemeData theme;

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

    // Crosshair + tooltip de la vela activa.
    final idx = activeIndex;
    if (idx != null && idx >= 0 && idx < bars.length) {
      _paintCrosshairAndTooltip(canvas, size, bars[idx], slot * idx + slot / 2, yFor);
    }
  }

  void _paintCrosshairAndTooltip(
    Canvas canvas,
    Size size,
    PriceBar bar,
    double cx,
    double Function(double) yFor,
  ) {
    // Línea guía vertical.
    final guide = Paint()
      ..color = theme.colorScheme.onSurface.withValues(alpha: 0.35)
      ..strokeWidth = 1;
    canvas.drawLine(Offset(cx, 0), Offset(cx, size.height), guide);

    // Punto sobre el cierre.
    final closeY = yFor(bar.close);
    canvas.drawCircle(
      Offset(cx, closeY),
      3,
      Paint()..color = theme.colorScheme.primary,
    );

    // Texto del tooltip.
    final priceFmt = NumberFormat('#,##0.00');
    final dateFmt = DateFormat('dd/MM/yyyy HH:mm');
    final lines = <String>[
      dateFmt.format(bar.openTime.toLocal()),
      'O ${priceFmt.format(bar.open)}   H ${priceFmt.format(bar.high)}',
      'L ${priceFmt.format(bar.low)}   C ${priceFmt.format(bar.close)}',
    ];
    final textStyle = TextStyle(
      color: theme.colorScheme.onInverseSurface,
      fontSize: 11,
    );
    final painters = lines
        .map((t) => TextPainter(
              text: TextSpan(text: t, style: textStyle),
              textDirection: TextDirection.ltr,
            )..layout())
        .toList();

    final boxWidth =
        painters.map((p) => p.width).reduce((a, b) => a > b ? a : b) + 16;
    final boxHeight =
        painters.fold<double>(0, (sum, p) => sum + p.height) + 12;

    // Posiciona el recuadro evitando salirse por la derecha.
    var boxLeft = cx + 8;
    if (boxLeft + boxWidth > size.width) boxLeft = cx - 8 - boxWidth;
    if (boxLeft < 0) boxLeft = 0;
    const boxTop = 4.0;

    final bgRect = RRect.fromRectAndRadius(
      Rect.fromLTWH(boxLeft, boxTop, boxWidth, boxHeight),
      const Radius.circular(6),
    );
    canvas.drawRRect(
      bgRect,
      Paint()..color = theme.colorScheme.inverseSurface.withValues(alpha: 0.92),
    );

    var y = boxTop + 6;
    for (final p in painters) {
      p.paint(canvas, Offset(boxLeft + 8, y));
      y += p.height;
    }
  }

  @override
  bool shouldRepaint(covariant _CandlePainter oldDelegate) =>
      oldDelegate.bars != bars || oldDelegate.activeIndex != activeIndex;
}
