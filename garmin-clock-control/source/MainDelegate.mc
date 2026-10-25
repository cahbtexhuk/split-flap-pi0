import Toybox.Communications;
import Toybox.Lang;
import Toybox.WatchUi;

const TIME_URL = "http://watch.hass.sphynx.works/time";

class MainDelegate extends WatchUi.Menu2InputDelegate {

    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item as MenuItem) as Void {
        sendTime(item.getId() as String);
    }

    function sendTime(value as String) as Void {
        var options = {
            :method => Communications.HTTP_REQUEST_METHOD_POST,
            :headers => { "Content-Type" => Communications.REQUEST_CONTENT_TYPE_JSON },
            :responseType => Communications.HTTP_RESPONSE_CONTENT_TYPE_TEXT_PLAIN
        };
        Communications.makeWebRequest(TIME_URL, { "value" => value }, options, method(:onResponse));
    }

    function onResponse(code as Number, data as Dictionary or String or Null) as Void {
        WatchUi.showToast(code == 200 ? "Sent" : "Failed (" + code + ")", null);
    }
}
