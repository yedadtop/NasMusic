package com.nasmusic.tv;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Enumeration;

/**
 * 给手机用的设置页 HTTP 服务。
 *
 * <p>遥控器改地址太难受，菜单键又可能被桌面的无障碍服务截走，所以干脆在电视上起一个
 * 极轻的 HTTP 服务：手机扫码 → 浏览器打开 → 填地址 → 保存，电视端立刻生效。</p>
 *
 * <p>只用 ServerSocket 手写最小 HTTP，不引框架：电视只有 1GB 内存，一个监听线程 +
 * 每请求一个短命线程足够，常驻开销可以忽略。</p>
 */
public final class SettingsServer {

    private static final String TAG = "NasMusic";
    public static final int PORT = 8088;

    /** 与 MainActivity 保持一致（那边是 private，这里复制一份避免改可见性） */
    static final String PREFS = "nasmusic_tv";
    static final String KEY_BASE = "server_base";
    static final String DEFAULT_BASE = "http://10.0.0.8";

    private static volatile boolean running = false;
    private static ServerSocket server;
    private static Context app;

    private SettingsServer() {
    }

    public static synchronized void start(Context ctx) {
        if (running) {
            return;
        }
        app = ctx.getApplicationContext();
        running = true;
        Thread t = new Thread(SettingsServer::acceptLoop, "nasmusic-settings-http");
        t.setDaemon(true);
        t.start();
    }

    public static synchronized void stop() {
        running = false;
        if (server != null) {
            try {
                server.close();
            } catch (Exception ignored) {
            }
            server = null;
        }
    }

    public static boolean isRunning() {
        return running;
    }

    /** 电视在局域网里的 IPv4，优先 wlan/eth，拿不到返回 null */
    public static String localIp() {
        try {
            Enumeration<NetworkInterface> ifs = NetworkInterface.getNetworkInterfaces();
            while (ifs != null && ifs.hasMoreElements()) {
                NetworkInterface nif = ifs.nextElement();
                if (!nif.isUp() || nif.isLoopback()) {
                    continue;
                }
                String name = nif.getName();
                if (!name.startsWith("wlan") && !name.startsWith("eth")) {
                    continue;
                }
                for (InterfaceAddress ia : nif.getInterfaceAddresses()) {
                    InetAddress a = ia.getAddress();
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) {
                        return a.getHostAddress();
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "localIp failed: " + e);
        }
        return null;
    }

    public static String url() {
        String ip = localIp();
        return ip == null ? null : "http://" + ip + ":" + PORT + "/";
    }

    /* ---------------- HTTP ---------------- */

    private static void acceptLoop() {
        try {
            server = new ServerSocket(PORT);
            Log.i(TAG, "settings http listening on " + PORT);
            while (running) {
                final Socket s = server.accept();
                Thread t = new Thread(() -> handle(s), "nasmusic-http-req");
                t.setDaemon(true);
                t.start();
            }
        } catch (Exception e) {
            if (running) {
                Log.w(TAG, "settings http stopped: " + e);
            }
        }
    }

    private static void handle(Socket s) {
        try {
            s.setSoTimeout(8000);
            InputStream in = new BufferedInputStream(s.getInputStream());
            ByteArrayOutputStream head = new ByteArrayOutputStream(1024);

            int prev3 = -1, prev2 = -1, prev1 = -1, cur;
            // 读到 \r\n\r\n 为止
            while ((cur = in.read()) != -1) {
                head.write(cur);
                if (prev3 == '\r' && prev2 == '\n' && prev1 == '\r' && cur == '\n') {
                    break;
                }
                prev3 = prev2;
                prev2 = prev1;
                prev1 = cur;
            }

            String headerText = head.toString(StandardCharsets.ISO_8859_1.name());
            String[] lines = headerText.split("\r\n");
            if (lines.length == 0 || lines[0].isEmpty()) {
                respond(s, 400, "text/plain; charset=utf-8", "bad request");
                return;
            }

            String[] reqLine = lines[0].split(" ");
            String method = reqLine.length > 0 ? reqLine[0] : "GET";
            String path = reqLine.length > 1 ? reqLine[1] : "/";
            int q = path.indexOf('?');
            String query = q >= 0 ? path.substring(q + 1) : "";
            if (q >= 0) {
                path = path.substring(0, q);
            }

            int contentLength = 0;
            for (String line : lines) {
                int c = line.indexOf(':');
                if (c > 0 && line.substring(0, c).trim().equalsIgnoreCase("Content-Length")) {
                    try {
                        contentLength = Integer.parseInt(line.substring(c + 1).trim());
                    } catch (NumberFormatException ignored) {
                    }
                }
            }

            String body = "";
            if (contentLength > 0 && contentLength < 65536) {
                byte[] buf = new byte[contentLength];
                int read = 0;
                while (read < contentLength) {
                    int n = in.read(buf, read, contentLength - read);
                    if (n < 0) {
                        break;
                    }
                    read += n;
                }
                body = new String(buf, 0, read, StandardCharsets.UTF_8);
            }

            if ("POST".equals(method) && "/save".equals(path)) {
                save(body);
                respond(s, 200, "text/html; charset=utf-8", pageSaved());
            } else if ("GET".equals(method) && "/api/config".equals(path)) {
                respond(s, 200, "application/json; charset=utf-8",
                        "{\"base\":\"" + json(currentBase()) + "\"}");
            } else if ("GET".equals(method) && "/".equals(path)) {
                respond(s, 200, "text/html; charset=utf-8", pageForm(""));
            } else {
                respond(s, 404, "text/plain; charset=utf-8", "not found");
            }
        } catch (Exception e) {
            Log.w(TAG, "http handle: " + e);
        } finally {
            try {
                s.close();
            } catch (Exception ignored) {
            }
        }
    }

    private static void respond(Socket s, int code, String type, String body) {
        try {
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            OutputStream out = s.getOutputStream();
            String head = "HTTP/1.1 " + code + (code == 200 ? " OK" : " Error") + "\r\n"
                    + "Content-Type: " + type + "\r\n"
                    + "Content-Length: " + bytes.length + "\r\n"
                    + "Cache-Control: no-store\r\n"
                    + "Connection: close\r\n\r\n";
            out.write(head.getBytes(StandardCharsets.ISO_8859_1));
            out.write(bytes);
            out.flush();
        } catch (Exception e) {
            Log.w(TAG, "respond: " + e);
        }
    }

    private static String currentBase() {
        return app == null ? DEFAULT_BASE
                : app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(KEY_BASE, DEFAULT_BASE);
    }

    private static void save(String formBody) {
        String value = null;
        for (String pair : formBody.split("&")) {
            int eq = pair.indexOf('=');
            if (eq <= 0) {
                continue;
            }
            String k = pair.substring(0, eq);
            if (!"base".equals(k)) {
                continue;
            }
            try {
                value = URLDecoder.decode(pair.substring(eq + 1), "UTF-8");
            } catch (Exception e) {
                value = pair.substring(eq + 1);
            }
        }
        if (value == null) {
            return;
        }
        String b = value.trim();
        if (b.isEmpty()) {
            b = DEFAULT_BASE;
        }
        if (!b.startsWith("http://") && !b.startsWith("https://")) {
            b = "http://" + b;
        }
        while (b.endsWith("/")) {
            b = b.substring(0, b.length() - 1);
        }
        // 内存里的 Api 与落盘的偏好一起改：电视端下一次请求就用新地址
        Api.setBase(b);
        SharedPreferences sp = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        sp.edit().putString(KEY_BASE, b).apply();
        Log.i(TAG, "base saved from web: " + b);
    }

    private static String json(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    /* ---------------- 页面 ---------------- */

    private static String shell(String inner) {
        return "<!DOCTYPE html><html lang=\"zh\"><head><meta charset=\"utf-8\">"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                + "<title>NasMusic 设置</title><style>"
                + "*{box-sizing:border-box}"
                + "body{margin:0;padding:28px 20px;background:#000;color:#fff;"
                + "font:16px/1.5 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}"
                + "h1{margin:0 0 4px;font-size:22px;letter-spacing:-.02em}"
                + "p.sub{margin:0 0 24px;color:#6E6E73;font-size:14px}"
                + "label{display:block;margin:0 0 8px;color:#A1A1A6;font-size:13px}"
                + "input{width:100%;padding:14px 16px;border-radius:12px;border:1px solid #2C2C2E;"
                + "background:#1C1C1E;color:#fff;font-size:16px;outline:none}"
                + "input:focus{border-color:#FA2D48}"
                + "button{width:100%;margin-top:16px;padding:15px;border:0;border-radius:12px;"
                + "background:#FA2D48;color:#fff;font-size:16px;font-weight:600}"
                + "button:active{opacity:.8}"
                + ".hint{margin-top:18px;color:#6E6E73;font-size:13px;line-height:1.7}"
                + ".ok{color:#32D74B;font-size:17px;margin-bottom:16px}"
                + "code{background:#1C1C1E;padding:2px 6px;border-radius:5px;color:#fff}"
                + "a{color:#FA2D48;text-decoration:none}"
                + "</style></head><body>" + inner + "</body></html>";
    }

    private static String pageForm(String message) {
        String base = currentBase();
        return shell("<h1>NasMusic 设置</h1>"
                + "<p class=\"sub\">电视端后端地址</p>"
                + (message.isEmpty() ? "" : "<p class=\"ok\">" + message + "</p>")
                + "<form method=\"POST\" action=\"/save\">"
                + "<label for=\"base\">服务器地址</label>"
                + "<input id=\"base\" name=\"base\" value=\"" + html(base) + "\" "
                + "placeholder=\"http://192.168.1.8\" autocomplete=\"off\" autocapitalize=\"off\">"
                + "<button type=\"submit\">保存</button></form>"
                + "<p class=\"hint\">填 NasMusic 网页版所在的主机和端口，例如 "
                + "<code>http://192.168.1.8</code>。保存后电视立即生效，不用重启。</p>");
    }

    private static String pageSaved() {
        return shell("<h1>已保存</h1>"
                + "<p class=\"ok\">电视端已切换到 <code>" + html(currentBase()) + "</code></p>"
                + "<p class=\"hint\">回到电视按返回键，或重新进入音乐库即可看到新数据。</p>"
                + "<p class=\"hint\"><a href=\"/\">继续修改</a></p>");
    }

    private static String html(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;");
    }
}
