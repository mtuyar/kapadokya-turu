"""Editor penceresinde: motor oturduktan sonra MetaHuman uretir ve editoru kapatir (KMH ortam degiskeni)."""
import runpy, os, traceback
import unreal
T = {"t": 0.0, "done": False}
H = None


def tick(dt):
    if T["done"]:
        return
    T["t"] += dt
    if T["t"] < 25.0:
        return
    T["done"] = True
    try:
        runpy.run_path(os.path.join(os.environ["KTOOLS"], "ue_mh_build.py"))
    except Exception:
        unreal.log_error("MHB HATA " + traceback.format_exc())
    unreal.log("MHB EDITOR KAPANIYOR")
    unreal.SystemLibrary.quit_editor()


H = unreal.register_slate_post_tick_callback(tick)
unreal.log("MHB zamanlayici kuruldu")
