package com.twobitoperations.roboburn;

import android.os.Bundle;
import android.os.Handler;
import android.os.Message;
import android.text.Editable;
import android.text.TextWatcher;
import android.util.Log;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;

import com.twobitoperations.roboburn.temp.BurnerStatus;
import com.twobitoperations.roboburn.temp.TempUtil;
import com.twobitoperations.roboburn.temp.ThermocoupleRead;

import java.io.IOException;

public class BurnStatusHandler extends Handler {
    final int burnColor = 0xffff0100;
    final int waitColor = 0xff0015ff;
    final TextView sense;
    final TextView food;
    final TextView burn;
    final TextView wait;
    final TextView modeIn;
    final TextView highIn;
    final TextView lowIn;
    final EditText high;
    final EditText low;
    final Spinner mode;
    final Button save;
    final ArrayAdapter<CharSequence> modes;
    final BurnerControlService service;

    public BurnStatusHandler(TextView sense, TextView food, TextView burn, TextView wait, TextView modeIn, TextView highIn, TextView lowIn, final EditText high, final EditText low, final Spinner mode, Button save, final ArrayAdapter<CharSequence> modes, final BurnerControlService service) {
        this.sense = sense;
        this.food = food;
        this.burn = burn;
        this.wait = wait;
        this.highIn = highIn;
        this.lowIn = lowIn;
        this.high = high;
        this.modeIn = modeIn;
        this.low = low;
        this.mode = mode;
        this.save = save;
        this.modes = modes;
        this.service = service;

        this.save.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                final Double high_val = TempUtil.fToC(Double.valueOf(high.getText().toString()));
                final Double low_val = TempUtil.fToC(Double.valueOf(low.getText().toString()));
                final String newMode = modes.getItem(mode.getSelectedItemPosition()).toString();

                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        Log.i(Burn.TAG, "setting temps to " + high_val + " " + low_val);
                        try {
                            service.setHigh(high_val.toString()).execute();
                            service.setLow(low_val.toString()).execute();
                            service.setMode(newMode).execute();
                        } catch (IOException e) {
                            Log.e(Burn.TAG, "unable to set", e);
                        }

                        Log.i(Burn.TAG, "setting mode to " + newMode);
                    }
                }).start();
            }
        });
    }

    @Override
    public void handleMessage(final Message message) {
        final Bundle bundle = message.getData();
        final BurnerStatus burnerStatus = (BurnerStatus)bundle.getSerializable(Burn.KEY_STATUS);

        if (burnerStatus != null) {
            updateTempText(burnerStatus.getTemp_sense(), this.sense);
            updateTempText(burnerStatus.getTemp_food(), this.food);

            updateBoolean(burnerStatus.isBurn(), burn, burnColor);
            updateBoolean(burnerStatus.isWait(), wait, waitColor);
            modeIn.setText(burnerStatus.getMode().toString());
            lowIn.setText(String.format("%2.1f F", TempUtil.cToF(burnerStatus.getLow_temp())));
            highIn.setText(String.format("%2.1f F", TempUtil.cToF(burnerStatus.getHigh_temp())));
        }
    }

    private void updateBoolean(final boolean enabled, final TextView field, final int enabledColor) {
        if (enabled) {
            field.setBackgroundColor(enabledColor);
            field.setTextColor(0xffffffff);
        } else {
            field.setBackgroundColor(0xffffffff);
            field.setTextColor(enabledColor);
        }
    }

    private void updateTempText(ThermocoupleRead read, TextView textView) {
        if (read == null) {
            return;
        }

        if (read.isFault()) {
            textView.setText("FAULT");
        } else {
            textView.setText(String.format("%2.1f F", read.getProbeF()));
        }
    }
}
