# What's all this, then?
This is a project that aims to control a food cooking system of some sort.

Frying a turkey? Look no further.
Brewing beer? Right here.
Smoking a stuff or thing? Boom. This'll get er' done.

The raspberry pi part of the code runs in python. It senses cooking fluid (air, oil, whatever,) temperature, and turns on or off a relay that runs your heat system to keep everything toasty.

The UI is a webapp served up by flask.

# Hardware
## pi


# Author's Notes:
For frying a turkey, I use a burner control system inspired by this page: http://www.homebrewtalk.com/f253/gas-temperature-control-dummies-116632/

The system is a Honeywell burner controller driving a low pressure LP burner.
 
- Honeywell VR8345Q4563 two stage valve. (Includes LP conversion, I installed it.) 
- Honeywell S8600C valve controller.
  - NOTE: this requires a separate sense probe to detect the flame. Other controllers in the series do not. I strongly suggest the S8600M instead.)
  - NOTE: the "main/stage 1" relay from this code will just power up the 24v of the controller. "high/stage 2" will connect directly to the "HI" terminal on the two-stage valve.
- Honeywell Q345A1313 pilot assy (includes LP conversion, I installed it.)
- Honeywell Q3620 heater/sense probe assy. (Only need the probe, and not needed at all if you choose the S8600M controller.)
- 24VAC transformer 
  - https://www.amazon.com/gp/product/B004VMVDTA/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Camco LP Regulator
  - https://www.amazon.com/gp/product/B0024ECBMA/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Big 32-jet LP Burner
  - http://www.ebay.com/itm/32-Tip-Jet-Burner-Propane-LP-Perfect-for-Wok-ranges-and-Pot-Ranges-/300915643063?ssPageName=ADME:L:OC:US:3160
  - NOTE: bayou classic or other LP burners will work too with some modifications. these cheap burners typically have an adjustable 1-20psi regulator (the honeywell valves work really hard to do 11"WC==0.4psi). If you want to use these burners, you'll need to modify the orifice they usually have at the point where the propane hose connects to the body of the burner. Increase the diameter of the orifice, and you should be able to make it work. The flame will probably burn pretty dirty, but it will burn with many BTUs. Failure to make this adjustment will get you a teeny tiny flame for babies.
- Camco LP Tank-To-Regulator
  - http://www.amazon.com/gp/product/B007HG7SM8/ref=oh_aui_search_detailpage?ie=UTF8&psc=1
- Some flex tubing
  - http://www.amazon.com/gp/product/B000AM8T38/ref=oh_aui_search_detailpage?ie=UTF8&psc=1

