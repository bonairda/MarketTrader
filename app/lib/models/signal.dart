/// Señal de un activo con su riesgo (proviene de /signals/{symbol}).
class TradingSignal {
  final String symbol;
  final String action; // BUY | SELL | HOLD | WATCH
  final int score;
  final int confidence;
  final List<String> rationale;
  final int riskScore;
  final String riskLevel; // LOW | MEDIUM | HIGH
  final List<String> riskFactors;

  const TradingSignal({
    required this.symbol,
    required this.action,
    required this.score,
    required this.confidence,
    required this.rationale,
    required this.riskScore,
    required this.riskLevel,
    required this.riskFactors,
  });

  factory TradingSignal.fromJson(Map<String, dynamic> json) {
    final risk = (json['risk'] as Map<String, dynamic>?) ?? {};
    List<String> strList(dynamic v) =>
        ((v as List<dynamic>?) ?? []).map((e) => e as String).toList();
    return TradingSignal(
      symbol: json['symbol'] as String,
      action: json['action'] as String,
      score: (json['score'] as num).toInt(),
      confidence: (json['confidence'] as num).toInt(),
      rationale: strList(json['rationale']),
      riskScore: (risk['score'] as num?)?.toInt() ?? 0,
      riskLevel: (risk['level'] as String?) ?? 'LOW',
      riskFactors: strList(risk['factors']),
    );
  }
}
