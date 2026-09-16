/// Evento corporativo: dividendo (con retención) o split.
class CorporateEvent {
  const CorporateEvent({
    required this.id,
    required this.assetId,
    required this.type,
    required this.eventDate,
    this.grossAmountOriginal,
    this.withholdingOriginal,
    this.currency,
    this.grossAmountEur,
    this.withholdingEur,
    this.netAmountEur,
    this.ratio,
    this.notes,
  });

  final String id;
  final String assetId;
  final String type;
  final String eventDate;
  final String? grossAmountOriginal;
  final String? withholdingOriginal;
  final String? currency;
  final String? grossAmountEur;
  final String? withholdingEur;
  final String? netAmountEur;
  final String? ratio;
  final String? notes;

  bool get isDividend => type == 'DIVIDEND';

  factory CorporateEvent.fromJson(Map<String, dynamic> json) => CorporateEvent(
        id: json['id'].toString(),
        assetId: json['assetId'].toString(),
        type: json['type'].toString(),
        eventDate: json['eventDate'].toString(),
        grossAmountOriginal: json['grossAmountOriginal'] as String?,
        withholdingOriginal: json['withholdingOriginal'] as String?,
        currency: json['currency'] as String?,
        grossAmountEur: json['grossAmountEur'] as String?,
        withholdingEur: json['withholdingEur'] as String?,
        netAmountEur: json['netAmountEur'] as String?,
        ratio: json['ratio'] as String?,
        notes: json['notes'] as String?,
      );
}

/// Payload para crear un evento corporativo.
class NewCorporateEvent {
  const NewCorporateEvent({
    required this.assetId,
    required this.type,
    required this.eventDate,
    this.grossAmountOriginal,
    this.withholdingOriginal,
    this.currency,
    this.ratio,
    this.notes,
  });

  final String assetId;
  final String type;
  final String eventDate;
  final String? grossAmountOriginal;
  final String? withholdingOriginal;
  final String? currency;
  final String? ratio;
  final String? notes;

  Map<String, dynamic> toJson() => {
        'assetId': assetId,
        'type': type,
        'eventDate': eventDate,
        if (grossAmountOriginal != null) 'grossAmountOriginal': grossAmountOriginal,
        if (withholdingOriginal != null) 'withholdingOriginal': withholdingOriginal,
        if (currency != null && currency!.isNotEmpty) 'currency': currency,
        if (ratio != null) 'ratio': ratio,
        if (notes != null && notes!.isNotEmpty) 'notes': notes,
      };
}
