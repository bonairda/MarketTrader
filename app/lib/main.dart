import 'package:flutter/material.dart';

import 'services/market_api.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const MarketTrackerApp());
}

class MarketTrackerApp extends StatefulWidget {
  const MarketTrackerApp({super.key});

  @override
  State<MarketTrackerApp> createState() => _MarketTrackerAppState();
}

class _MarketTrackerAppState extends State<MarketTrackerApp> {
  final MarketApi _api = MarketApi();

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MarketTracker',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF1E88E5),
        useMaterial3: true,
      ),
      home: HomeScreen(api: _api),
    );
  }
}
