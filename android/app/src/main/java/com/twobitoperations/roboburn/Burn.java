package com.twobitoperations.roboburn;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;

import com.androidplot.xy.LineAndPointFormatter;
import com.androidplot.xy.PointLabelFormatter;
import com.androidplot.xy.XYPlot;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.twobitoperations.roboburn.convert.JacksonConverter;

import retrofit.RestAdapter;

public class Burn extends Activity {
    protected BurnerControlService burnerService;
    public static final String TAG = "burn";
    public static final String KEY_STATUS = "status";
    private ArrayAdapter<CharSequence> modes;
    private Spinner mode;

    protected TimerThread timerThread;
    protected LineAndPointFormatter statusFormat;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_burn);

        statusFormat = new LineAndPointFormatter();
        statusFormat.setPointLabelFormatter(new PointLabelFormatter());
        statusFormat.configure(getApplicationContext(),
                R.xml.line_point_formatter_with_plf1);

        modes = ArrayAdapter.createFromResource(this, R.array.modes, R.layout.spin_big);
        mode = (Spinner)findViewById(R.id.mode);

        startHandlers();
    }

    private synchronized void startHandlers() {
        if (timerThread == null) {
            SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(this);
            final String endpoint = sharedPref.getString("ip", "http://192.168.5.114:8088");

            final RestAdapter restAdapter = new RestAdapter.Builder().setEndpoint(endpoint)
                    .setConverter(new JacksonConverter(new ObjectMapper()))
                    .build();

            this.burnerService = restAdapter.create(BurnerControlService.class);

            final XYPlot plot =(XYPlot) findViewById(R.id.tempPlot);
            final BurnPlotHandler plotHandler = new BurnPlotHandler(plot, statusFormat);

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
        }
        return super.onOptionsItemSelected(item);
    }
}
