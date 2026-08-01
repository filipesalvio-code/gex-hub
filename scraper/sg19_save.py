import sys

sys.path.insert(0, 'scraper')
from db_writer import finish_run, save_snapshot

spy_greeks = {
  "url": "https://dashboard.spotgamma.com/indices?sym=SPY", "title": "SPY Indices - SpotGamma",
  "section": "indices", "symbol": "SPY", "view_tab": "Greeks",
  "charts": {
    "SPY Gamma Model": {"legend": ["Jul 24","Jul 23","Jul 22"], "x_axis_label": "Strike", "x_axis_ticks": ["$668","$708","$748","$812"], "y_axis_label": "Gamma Notional", "y_axis_ticks": ["-$2.7B","-$1.2B","$1.4B"], "chart_only": True},
    "SPY Delta Model": {"legend": ["Jul 24","Jul 23","Jul 22"], "x_axis_label": "Strike", "x_axis_ticks": ["$668","$708","$748","$812"], "y_axis_label": "Delta Notional", "y_axis_ticks": ["-$280B","-$130B","$20B","$313B"], "chart_only": True},
    "SPY Vanna Model": {"legend": ["Jul 24","Jul 23","Jul 22"], "x_axis_label": "Spot", "x_axis_ticks": ["$713","$728","$743","$763"], "y_axis_label": "Delta Notional", "y_axis_ticks": ["$2B","$2.4B","$2.8B","$3.5B"], "chart_only": True},
    "SPY Absolute Gamma": {"sub_tabs": ["Total","Next Expiration"], "x_axis_label": "Strike", "x_axis_ticks": ["$659","$704","$749","$826"], "y_axis_label": "Gamma", "y_axis_ticks": ["$-401M","$-251M","$-101M","$140M"], "range_labels": ["$659","$826"], "chart_only": True},
    "SPY Combo Strikes": {"sub_tabs": ["Total","Next Expiration"], "x_axis_label": "Strike", "x_axis_ticks": ["$702","$711","$720","$729","$738","$747","$756","$765","$774"], "y_axis_label": "Gamma", "y_axis_ticks": ["-$45M","-$30M","-$15M","$14M"], "chart_only": True},
    "SPY Gamma Tilt Chart": {"legend": ["Gamma","Delta"], "x_axis_label": "Trade Date", "x_axis_ticks": ["2021-09-20","2022-09-02","2023-08-16","2024-07-28","2025-07-10","2026-07-23"], "range_labels": ["2021-03-31","2026-07-23"], "left_y_axis_label": "Price", "left_y_axis_ticks": ["$356","$506","$759"], "right_y_axis_label": "Tilt", "right_y_axis_ticks": ["0.19","0.69","1.2","2"], "chart_only": True},
    "SPY Expiration Concentration": {"x_axis_label": "expiration", "x_axis_ticks": ["2026-07-24","2026-08-04","2026-08-31","2026-11-30","2028-12-15"], "range_labels": ["2026-07-24","2028-12-15"], "y_axis_label": "Delta Notional", "y_axis_ticks": ["-$24.7B","-$9.71B","$15.4B"], "chart_only": True},
    "SPY Historical Chart": {"chart_only": True, "note": "no text labels in SVG"}
  },
  "tables": {
    "SPY Concentration Table": {"headers": [], "rows": [], "note": "empty - market closed weekend"},
    "SPY Strike Table": {"headers": [], "rows": [], "note": "empty - market closed weekend"}
  },
  "extra_page_text": "-$24.7B"
}
print(save_snapshot(21, "https://dashboard.spotgamma.com/indices?sym=SPY", "indices", spy_greeks))
finish_run(21, 'ok', 'items=9 snapshots; symbols=SPX,SPY,NDX,QQQ,RUT,IWM; views=Greeks(all)+Volatility(SPX)+OI(SPX,NDX); quote strip blank (market closed); Concentration/Strike tables empty (weekend); all chart series values chart_only (SVG paths), axis/legend text captured')
print('finished')
