package com.twobitoperations.roboburn;

import android.os.Bundle;
import android.os.Handler;
import android.os.Message;

import com.androidplot.Series;
import com.androidplot.ui.SeriesAndFormatter;
import com.androidplot.xy.LineAndPointFormatter;
import com.androidplot.xy.XYPlot;
import com.androidplot.xy.XYSeries;
import com.androidplot.xy.XYSeriesFormatter;
import com.androidplot.xy.XYStepMode;
import com.androidplot.xy.YValueMarker;
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
    protected final LineAndPointFormatter statusFormatter;

    public BurnPlotHandler(XYPlot plot, LineAndPointFormatter statusFormatter) {
        this.plot = plot;
        this.statusFormatter = statusFormatter;

        this.sense = new DynamicSeries("sense");
        this.food = new DynamicSeries("food");

        this.high_marker = new YValueMarker(0, "high");
        this.low_marker = new YValueMarker(0, "low");

        plot.addMarker(high_marker);
        plot.addMarker(low_marker);

        for (final SeriesAndFormatter<XYSeries, XYSeriesFormatter> s : plot.getSeriesRegistry()) {
            plot.removeSeries(s.getSeries());
        }

        plot.addSeries(sense, statusFormatter);
        plot.addSeries(food, statusFormatter);


        // reduce the number of range labels
        plot.setTicksPerRangeLabel(3);
        plot.setTicksPerDomainLabel(Integer.MAX_VALUE);
        statusFormatter.setPointLabeler(null);
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
