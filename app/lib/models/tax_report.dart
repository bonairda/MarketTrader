class TaxSummary {
  const TaxSummary({
    required this.sellOperations,
    required this.matchedLots,
    required this.proceedsEur,
    required this.acquisitionCostEur,
    required this.feesEur,
    required this.realizedGainEur,
  });

  final int sellOperations;
  final int matchedLots;
  final String proceedsEur;
  final String acquisitionCostEur;
  final String feesEur;
  final String realizedGainEur;

  factory TaxSummary.fromJson(Map<String, dynamic> json) => TaxSummary(
        sellOperations: (json['sellOperations'] as num).toInt(),
        matchedLots: (json['matchedLots'] as num).toInt(),
        proceedsEur: json['proceedsEur'].toString(),
        acquisitionCostEur: json['acquisitionCostEur'].toString(),
        feesEur: json['feesEur'].toString(),
        realizedGainEur: json['realizedGainEur'].toString(),
      );
}

class TaxAssetSummary {
  const TaxAssetSummary({
    required this.assetId,
    required this.quantitySold,
    required this.proceedsEur,
    required this.acquisitionCostEur,
    required this.feesEur,
    required this.realizedGainEur,
  });

  final String assetId;
  final String quantitySold;
  final String proceedsEur;
  final String acquisitionCostEur;
  final String feesEur;
  final String realizedGainEur;

  factory TaxAssetSummary.fromJson(Map<String, dynamic> json) => TaxAssetSummary(
        assetId: json['assetId'].toString(),
        quantitySold: json['quantitySold'].toString(),
        proceedsEur: json['proceedsEur'].toString(),
        acquisitionCostEur: json['acquisitionCostEur'].toString(),
        feesEur: json['feesEur'].toString(),
        realizedGainEur: json['realizedGainEur'].toString(),
      );
}

class TaxDisposal {
  const TaxDisposal({
    required this.assetId,
    required this.sellOperationId,
    required this.saleDate,
    required this.buyOperationId,
    required this.acquisitionDate,
    required this.matchedQuantity,
    required this.proceedsEur,
    required this.acquisitionCostEur,
    required this.gainEur,
  });

  final String assetId;
  final String sellOperationId;
  final String saleDate;
  final String buyOperationId;
  final String acquisitionDate;
  final String matchedQuantity;
  final String proceedsEur;
  final String acquisitionCostEur;
  final String gainEur;

  factory TaxDisposal.fromJson(Map<String, dynamic> json) => TaxDisposal(
        assetId: json['assetId'].toString(),
        sellOperationId: json['sellOperationId'].toString(),
        saleDate: json['saleDate'].toString(),
        buyOperationId: json['buyOperationId'].toString(),
        acquisitionDate: json['acquisitionDate'].toString(),
        matchedQuantity: json['matchedQuantity'].toString(),
        proceedsEur: json['proceedsEur'].toString(),
        acquisitionCostEur: json['acquisitionCostEur'].toString(),
        gainEur: json['gainEur'].toString(),
      );
}

class TaxReport {
  const TaxReport({
    required this.year,
    required this.currency,
    required this.summary,
    required this.assets,
    required this.disposals,
    required this.disclaimer,
  });

  final int year;
  final String currency;
  final TaxSummary summary;
  final List<TaxAssetSummary> assets;
  final List<TaxDisposal> disposals;
  final String disclaimer;

  factory TaxReport.fromJson(Map<String, dynamic> json) => TaxReport(
        year: (json['year'] as num).toInt(),
        currency: json['currency'].toString(),
        summary: TaxSummary.fromJson(json['summary'] as Map<String, dynamic>),
        assets: (json['assets'] as List<dynamic>)
            .map((e) => TaxAssetSummary.fromJson(e as Map<String, dynamic>))
            .toList(),
        disposals: (json['disposals'] as List<dynamic>)
            .map((e) => TaxDisposal.fromJson(e as Map<String, dynamic>))
            .toList(),
        disclaimer: json['disclaimer'].toString(),
      );
}
