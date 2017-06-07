package com.twobitoperations.roboburn;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;

import com.androidplot.xy.LineAndPointFormatter;
import com.androidplot.xy.XYPlot;
import com.androidplot.xy.XYStepMode;

import org.joda.time.DateTimeZone;
import org.joda.time.Instant;
import org.joda.time.LocalDateTime;

import java.text.DecimalFormat;
import java.text.FieldPosition;
import java.text.Format;
import java.text.ParsePosition;
import java.text.SimpleDateFormat;
import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import retrofit2.Retrofit;
import retrofit2.converter.jackson.JacksonConverterFactory;

public class Burn extends Activity {
    protected BurnerControlService burnerService;
    public static final String TAG = "burn";
    public static final String KEY_STATUS = "status";
    public static final String KEY_ERRORS = "error";
    public static final String KEY_INIT_SET = "initialSet";
    private ArrayAdapter<CharSequence> modes;
    private Spinner mode;

    protected TimerThread timerThread;
    protected LineAndPointFormatter burnFormat;
    protected LineAndPointFormatter foodFormat;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_burn);

        burnFormat = new LineAndPointFormatter(
                Color.RED, // line
                Color.RED, // vertex
                Color.TRANSPARENT, // fill
                null //labeler
        );

        foodFormat = new LineAndPointFormatter(
                Color.RED, // line
                Color.RED, // vertex
                Color.TRANSPARENT, // fill
                null //labeler
        );

        modes = ArrayAdapter.createFromResource(this, R.array.modes, R.layout.spin_big);
        mode = (Spinner)findViewById(R.id.mode);

        startHandlers();
    }

    public static class SimpleEpochMillisFormatter extends Format {
        final SimpleDateFormat simpleDateFormat = new SimpleDateFormat("HH:mm");

        @Override
        public StringBuffer format(Object o, StringBuffer stringBuffer, FieldPosition fieldPosition) {
            if (o instanceof Double) {
                final Double castDouble = (Double)o;
                final Instant i = new Instant(castDouble.longValue());
                final LocalDateTime localDateTime = new LocalDateTime(i, DateTimeZone.getDefault());
                return simpleDateFormat.format(localDateTime.toDate(), stringBuffer, fieldPosition);
            } else {
                return stringBuffer;
            }
        }

        @Override
        public Object parseObject(String s, ParsePosition parsePosition) {
            return null;
        }
    }

    private synchronized void startHandlers() {
        if (timerThread == null) {
            SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(this);
            final String endpoint = sharedPref.getString(SettingsActivity.KEY_IP, "http://roboburn:8088/");
            Log.i(Burn.TAG, "endpoint is " + endpoint);

            final OkHttpClient.Builder builder = new OkHttpClient.Builder();
            builder.connectTimeout(2500, TimeUnit.MILLISECONDS);
            builder.readTimeout(2500, TimeUnit.MILLISECONDS);

            final Retrofit restAdapter = new Retrofit.Builder()
                    .baseUrl(endpoint)
                    .addConverterFactory(JacksonConverterFactory.create())
                    .client(builder.build())
                    .build();

            this.burnerService = restAdapter.create(BurnerControlService.class);

            final XYPlot plot =(XYPlot) findViewById(R.id.tempPlot);
            final BurnPlotHandler plotHandler = new BurnPlotHandler(plot, burnFormat, foodFormat);
            plot.setDomainValueFormat(new SimpleEpochMillisFormatter());
            plot.setDomainStep(XYStepMode.SUBDIVIDE, 5);
            plot.setRangeValueFormat(new DecimalFormat("#"));
            plot.setRangeStep(XYStepMode.SUBDIVIDE, 5);

            final Spinner mode = (Spinner)findViewById(R.id.mode);
            mode.setAdapter(modes);
            final BurnStatusHandler statusHandler = new BurnStatusHandler(
                    (TextView)findViewById(R.id.sense),
                    (TextView)findViewById(R.id.food),
                    (TextView)findViewById(R.id.burn),
                    (TextView)findViewById(R.id.wait),
                    (TextView)findViewById(R.id.mode_in),
                    (TextView)findViewById(R.id.high_in),
                    (TextView)findViewById(R.id.low_in),
                    (EditText)findViewById(R.id.high_temp),
                    (EditText)findViewById(R.id.low_temp),
                    mode,
                    (Button)findViewById(R.id.save_temp),
                    modes,
                    burnerService);

            timerThread = new TimerThread(burnerService, plotHandler, statusHandler);
            final Thread t = new Thread(timerThread);
            t.start();
        }
    }

    @Override
    protected synchronized void onPause() {
        if (timerThread != null) {
            timerThread.setStopRequested(true);
            timerThread = null;
        }
        super.onPause();
    }

    @Override
    protected synchronized void onResume() {
        startHandlers();
        super.onResume();
    }


    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.burn, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();
        if (id == R.id.action_settings) {
            startActivity(new Intent(this, SettingsActivity.class));
        } else if (id == R.id.action_mdns) {
            startActivity(new Intent(this, MDNSDetector.class));
        }
        return super.onOptionsItemSelected(item);
    }
}
