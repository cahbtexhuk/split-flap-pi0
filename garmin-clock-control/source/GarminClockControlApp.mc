import Toybox.Application;
import Toybox.Lang;
import Toybox.WatchUi;

class GarminClockControlApp extends Application.AppBase {

    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() as [Views] or [Views, InputDelegates] {
        var menu = new WatchUi.Menu2({ :title => "Clock" });
        menu.addItem(new WatchUi.MenuItem("Reset", null, "reset", null));
        menu.addItem(new WatchUi.MenuItem("+30 min", null, "30m", null));
        menu.addItem(new WatchUi.MenuItem("+1 hour", null, "1h", null));
        menu.addItem(new WatchUi.MenuItem("+2 hours", null, "2h", null));
        return [menu, new MainDelegate()];
    }
}

function getApp() as GarminClockControlApp {
    return Application.getApp() as GarminClockControlApp;
}
