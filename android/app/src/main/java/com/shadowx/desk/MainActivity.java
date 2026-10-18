package com.shadowx.desk;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    static final int PORT = 5555, COLS = 5, ROWS = 3;

    final Handler ui = new Handler(Looper.getMainLooper());
    final ExecutorService sender = Executors.newSingleThreadExecutor();
    final FrameLayout[] cells = new FrameLayout[COLS * ROWS];
    final ImageView[] imgs = new ImageView[COLS * ROWS];
    final TextView[] labels = new TextView[COLS * ROWS];
    TextView tvIp, tvPorta, tvUsb;
    View dot;
    Button btn;
    GradientDrawable dotBg;
    ServerSocket server;
    volatile Socket client;
    volatile PrintWriter out;
    volatile boolean running;
    float d;

    int dp(int v) { return Math.round(v * d); }

    GradientDrawable shape(int color, int radiusDp, int strokeColor) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radiusDp));
        if (strokeColor != 0) g.setStroke(dp(1), strokeColor);
        return g;
    }

    TextView pill(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextColor(Color.WHITE);
        t.setTextSize(14);
        t.setGravity(Gravity.CENTER_VERTICAL);
        t.setPadding(dp(16), 0, dp(16), 0);
        t.setBackgroundDrawable(shape(0xFF1B1B1B, 16, 0));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(32));
        lp.setMargins(dp(10), 0, dp(10), 0);
        t.setLayoutParams(lp);
        return t;
    }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        d = getResources().getDisplayMetrics().density;
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN
                | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xFF0E0A0A);
        root.setPadding(dp(8), dp(8), dp(8), dp(8));

        // cabeçalho
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        head.setPadding(dp(4), dp(2), dp(4), dp(2));
        head.setBackgroundDrawable(shape(0xFF100D0D, 14, 0xFF4A4444));
        dot = new View(this);
        dotBg = new GradientDrawable();
        dotBg.setShape(GradientDrawable.OVAL);
        dotBg.setColor(0xFFE8232B);
        dot.setBackgroundDrawable(dotBg);
        head.addView(dot, new LinearLayout.LayoutParams(dp(18), dp(18)));
        TextView title = new TextView(this);
        title.setText("ShadowX Desk");
        title.setTextColor(Color.WHITE);
        title.setTextSize(14);
        title.setPadding(dp(10), 0, 0, 0);
        head.addView(title);
        root.addView(head, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(28)));

        // grade 3x5
        LinearLayout grid = new LinearLayout(this);
        grid.setOrientation(LinearLayout.VERTICAL);
        root.addView(grid, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        for (int r = 0; r < ROWS; r++) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            grid.addView(row, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
            for (int c = 0; c < COLS; c++) {
                final int id = r * COLS + c;
                FrameLayout f = new FrameLayout(this);
                f.setBackgroundDrawable(shape(0xFF555555, 14, 0x55FFFFFF));
                ImageView iv = new ImageView(this);
                iv.setScaleType(ImageView.ScaleType.FIT_XY);
                f.addView(iv, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT));
                TextView tv = new TextView(this);
                tv.setTextColor(Color.WHITE);
                tv.setTypeface(Typeface.DEFAULT_BOLD);
                tv.setTextSize(14);
                tv.setGravity(Gravity.CENTER);
                tv.setPadding(0, dp(3), 0, dp(3));
                tv.setBackgroundColor(0x88000000);
                tv.setVisibility(View.GONE);
                f.addView(tv, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM));
                f.setOnClickListener(new View.OnClickListener() {
                    public void onClick(View v) { sendPress(id); }
                });
                f.setOnTouchListener(new View.OnTouchListener() {
                    public boolean onTouch(View v, MotionEvent e) {
                        int a = e.getAction();
                        if (a == MotionEvent.ACTION_DOWN) v.setAlpha(0.6f);
                        else if (a == MotionEvent.ACTION_UP || a == MotionEvent.ACTION_CANCEL) v.setAlpha(1f);
                        return false;
                    }
                });
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f);
                lp.setMargins(dp(8), dp(8), dp(8), dp(8));
                row.addView(f, lp);
                cells[id] = f; imgs[id] = iv; labels[id] = tv;
            }
        }

        // barra inferior
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(10), dp(4), dp(10), dp(4));
        bar.setBackgroundDrawable(shape(0xFF100D0D, 20, 0xFF3A3333));
        tvIp = pill("IP: -");
        tvPorta = pill("Porta: " + PORT);
        tvUsb = pill("USB: aguardando");
        bar.addView(tvIp);
        bar.addView(tvPorta);
        bar.addView(tvUsb);
        View space = new View(this);
        bar.addView(space, new LinearLayout.LayoutParams(0, 1, 1f));
        btn = new Button(this);
        btn.setText("Conectar");
        btn.setTextColor(Color.WHITE);
        btn.setTextSize(14);
        btn.setBackgroundDrawable(shape(0xFFE8232B, 16, 0));
        btn.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (running) stopServer(); else startServer();
            }
        });
        bar.addView(btn, new LinearLayout.LayoutParams(dp(130), dp(32)));
        root.addView(bar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(44)));

        setContentView(root);

        String saved = getSharedPreferences("cfg", MODE_PRIVATE).getString("config", null);
        if (saved != null) applyConfig(saved);
        startServer();
    }

    // ---------- servidor ----------
    void startServer() {
        if (running) return;
        running = true;
        btn.setText("Desconectar");
        tvIp.setText("IP: " + getIp());
        setStatus(false, false);
        new Thread(new Runnable() {
            public void run() {
                try {
                    server = new ServerSocket();
                    server.setReuseAddress(true);
                    server.bind(new InetSocketAddress(PORT));
                    while (running) {
                        Socket s = server.accept();
                        handle(s);
                    }
                } catch (Exception e) {
                    // servidor encerrado ou porta ocupada
                }
                running = false;
                ui.post(new Runnable() {
                    public void run() { btn.setText("Conectar"); setStatus(false, false); }
                });
            }
        }).start();
    }

    void stopServer() {
        running = false;
        try { if (client != null) client.close(); } catch (Exception e) { }
        try { if (server != null) server.close(); } catch (Exception e) { }
    }

    void handle(Socket s) {
        client = s;
        final boolean usb = s.getInetAddress().isLoopbackAddress();
        try {
            BufferedReader r = new BufferedReader(new InputStreamReader(s.getInputStream(), "UTF-8"));
            out = new PrintWriter(new OutputStreamWriter(s.getOutputStream(), "UTF-8"), true);
            out.println("{\"type\":\"hello\"}");
            setStatusAsync(true, usb);
            String line;
            while ((line = r.readLine()) != null) {
                final String l = line;
                ui.post(new Runnable() {
                    public void run() {
                        try {
                            if (new JSONObject(l).optString("type").equals("config")) {
                                getSharedPreferences("cfg", MODE_PRIVATE).edit().putString("config", l).commit();
                                applyConfig(l);
                            }
                        } catch (Exception e) { }
                    }
                });
            }
        } catch (Exception e) {
            // conexão caiu
        } finally {
            out = null;
            try { s.close(); } catch (Exception e) { }
            client = null;
            setStatusAsync(false, false);
        }
    }

    void sendPress(final int id) {
        sender.execute(new Runnable() {
            public void run() {
                PrintWriter o = out;
                if (o != null) o.println("{\"type\":\"press\",\"id\":" + id + "}");
            }
        });
    }

    // ---------- UI ----------
    void setStatusAsync(final boolean connected, final boolean usb) {
        ui.post(new Runnable() { public void run() { setStatus(connected, usb); } });
    }

    void setStatus(boolean connected, boolean usb) {
        dotBg.setColor(connected ? 0xFF2ECC71 : 0xFFE8232B);
        if (connected) tvUsb.setText(usb ? "USB: conectado" : "Wi-Fi: conectado");
        else tvUsb.setText("USB: aguardando");
    }

    void applyConfig(String json) {
        try {
            JSONArray a = new JSONObject(json).getJSONArray("buttons");
            for (int i = 0; i < cells.length; i++) {
                imgs[i].setImageBitmap(null);
                labels[i].setVisibility(View.GONE);
            }
            for (int k = 0; k < a.length(); k++) {
                JSONObject o = a.getJSONObject(k);
                int id = o.getInt("id");
                if (id < 0 || id >= cells.length) continue;
                String label = o.optString("label", "");
                if (label.length() > 0) {
                    labels[id].setText(label);
                    labels[id].setVisibility(View.VISIBLE);
                }
                String img = o.optString("img", "");
                if (img.length() > 0) {
                    byte[] bytes = Base64.decode(img, Base64.DEFAULT);
                    Bitmap bm = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
                    imgs[id].setImageBitmap(bm);
                }
            }
        } catch (Exception e) { }
    }

    String getIp() {
        try {
            WifiManager wm = (WifiManager) getSystemService(Context.WIFI_SERVICE);
            int ip = wm.getConnectionInfo().getIpAddress();
            if (ip == 0) return "sem Wi-Fi";
            return (ip & 0xff) + "." + ((ip >> 8) & 0xff) + "." + ((ip >> 16) & 0xff) + "." + ((ip >> 24) & 0xff);
        } catch (Exception e) {
            return "-";
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopServer();
        sender.shutdown();
    }
}
