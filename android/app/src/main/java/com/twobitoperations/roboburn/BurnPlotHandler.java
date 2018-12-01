package com.twobitoperations.roboburn;

import android.os.Bundle;
import android.os.Handler;
import android.os.Message;

import com.androidplot.xy.LineAndPointFormatter;
import com.androidplot.xy.XYPlot;
import com.androidplot.xy.XYSeries;
import com.androidplot.xy.YValueMarker;
import com.google.common.collect.ImmutableList;
import com.twobitoperations.roboburn.temp.BurnerStatus;

import java.util.List;

/**
* Created by armalota on 11/15/14.
*/
public class BurnPlotHandler extends Handler {
    protected final XYPlot plot;
    protected final DynamicSeries sense;
    protected final DynamicSeries food;
    protected final YValueMarker high_marker;
    protected final YValueMarker low_marker;
    protected final LineAndPointFormatter senseFormatter;
    protected final LineAndPointFormatter foodFormatter;

    public BurnPlotHandler(XYPlot plot, LineAndPointFormatter senseFormatter, LineAndPointFormatter foodFormatter) {
        this.plot = plot;
        this.senseFormatter = senseFormatter;
        this.foodFormatter = foodFormatter;

        this.sense = new DynamicSeries("sense");
        this.food = new DynamicSeries("food");

        this.high_marker = new YValueMarker(0, "high");
        this.low_marker = new YValueMarker(0, "low");

        plot.addMarker(high_marker);
        plot.addMarker(low_marker);

        final ImmutableList.Builder<XYSeries> seriesToRemove = ImmutableList.builder();
        for (final XYSeries s : plot.getRegistry().getSeriesList()) {
            seriesToRemove.add(s);
        }
        for (final XYSeries series : seriesToRemove.build()) {
            plot.getRegistry().remove(series);
        }

        plot.addSeries(sense, senseFormatter);
        plot.addSeries(food, foodFormatter);

        plot.redraw();
    }

    @Override
    public void handleMessage(Message msg) {
        final Bundle bundle = msg.getData();
        final BurnerStatus burnerStatus = (BurnerStatus)bundle.getSerializable(Burn.KEY_STATUS);

        if (burnerStatus != null) {
            // Create a couple arrays of y-values to plot:
            List<Number> statusNumbers = burnerStatus.getInterleavedSenseHistory();

            this.sense.setValues(statusNumbers);

            this.high_marker.setValue(burnerStatus.getHigh_temp());
            this.low_marker.setValue(burnerStatus.getHigh_temp());

            this.plot.redraw();
        }
    }
}
