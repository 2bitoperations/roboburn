# What's all this, then?
This is a project that aims to control a heating system of some sort.

Frying a turkey? Look no further.
Brewing beer? Right here.
Smoking a stuff or thing? Boom. This'll get er' done.

The raspberry pi part of the code runs in python. It senses cooking fluid (air, oil, whatever,) temperature using a Type-K thermocouple, and makes turns on or off a relay that runs your heat system to keep everything toasty.

The Android part runs on your phone or tablet to change heating setpoints and graph the current temps and whatnot.

# Hardware
## pi
- MAX6675 SPI-connected Type-K Thermocouple Interface (two of them, one for the cooking fluid, one for the food.)
  - got mine here: http://www.ebay.com/itm/MAX31855K-Single-ch-Type-K-Thermocouple-Breakout-270C-1372C-MAX6675-upgrade-/330866861746?ssPageName=ADME:L:OC:US:3160
- Type-K Thermocouple (again, two of them.)
  - got mine here: http://www.amazon.com/gp/product/B00843IKWK/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
  - they get angry if you let their sheaths touch. pick up some shrinkwrap to insulate them.
- Some relay module appropriate for your heater.
  - I use this one: http://www.amazon.com/gp/product/B00C59NOHK/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Other stuff:
  - Dry boxes are nice. I like this one: http://www.amazon.com/gp/product/B002KENWZY/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
  - If you use a wifi dongle w/ your pi, you might want a powered USB hub.

# Author's Notes:
For frying a turkey, I use a burner control system inspired by this page: http://www.homebrewtalk.com/f253/gas-temperature-control-dummies-116632/

The system is a Honeywell burner controller driving an low pressure LP burner.
 
- Honeywell Y8610U controller/valve (includes LP conversion, be sure to install it.)
  - bought new old stock on eBay
- Honeywell Q345A1313 pilot assy (includes LP conversion, be sure to install it.)
  - bought new on eBay
- 24VAC transformer 
  - https://www.amazon.com/gp/product/B004VMVDTA/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Camco LP Regulator
  - https://www.amazon.com/gp/product/B0024ECBMA/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Big 32-jet LP Burner
  - http://www.ebay.com/itm/32-Tip-Jet-Burner-Propane-LP-Perfect-for-Wok-ranges-and-Pot-Ranges-/300915643063?ssPageName=ADME:L:OC:US:3160
- Camco LP Tank-To-Regulator
  - http://www.amazon.com/gp/product/B007HG7SM8/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Some flex tubing
  - http://www.amazon.com/gp/product/B000AM8T38/ref=oh_aui_search_detailpage?ie=UTF8&psc=1

