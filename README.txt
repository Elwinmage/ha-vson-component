fishfeeder-roxane — slots fetched from the repo (for ESPHome Builder)

esphome-config/fishfeeder-roxane.yaml
    -> goes in Home Assistant, as the device YAML you edit in ESPHome Builder.
       It pulls each slot from the repo, so no local slots/ folder is needed.

repo-esphome/slots/feed_slot.yaml
    -> push into the ha-vson-component repo at:  esphome/slots/feed_slot.yaml
       (next to esphome/components/vson_feeder/). Commit & push before building.

While you are changing feed_slot.yaml in the repo, set "refresh: 1d" to
"refresh: 0s" in the packages block so a push is picked up immediately; put
it back to 1d afterwards.
