# MarketTracker — Cliente Flutter (ordenador, móvil y web)

App multiplataforma que consume la API del backend. Una sola base de código
para Windows/macOS/Linux (escritorio), Android/iOS (móvil) y web.

Ejecutar en cada plataforma:
- Escritorio Windows: `flutter run -d windows`
- Web (navegador): `flutter run -d chrome`
- Móvil: `flutter run -d <dispositivo/emulador>`
F1: watchlist en vivo + detalle de activo con velas.

## Estructura

```
lib/
├── core/config.dart          # URL base de la API y ajustes
├── models/                   # LivePrice, PriceBar
├── services/market_api.dart  # cliente HTTP de la API
├── widgets/candlestick_chart.dart  # gráfico de velas (CustomPainter)
├── screens/
│   ├── watchlist_screen.dart      # pantalla principal (precios en vivo)
│   └── asset_detail_screen.dart   # detalle con velas
└── main.dart
```

## Puesta en marcha

Este paquete contiene solo el código Dart (`lib/` + `pubspec.yaml`). Las carpetas
de plataforma (android/ios/web/...) se generan la primera vez:

```bash
cd app
flutter create .          # genera android/ios/web/windows/... conservando lib/ y pubspec
flutter pub get
flutter run
```

## Apuntar a la API

Por defecto usa `http://localhost:8000`. Para otro host:

```bash
# Emulador Android (el host es 10.0.2.2)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# Dispositivo físico / red local
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000
```

## Notas

- El precio en vivo se refresca por **polling REST** cada 3 s (MVP).
  Cuando el backend exponga el WebSocket gateway, se cambiará a streaming.
- El gráfico de velas es propio (CustomPainter), sin librerías externas, para
  mantener las dependencias al mínimo.
