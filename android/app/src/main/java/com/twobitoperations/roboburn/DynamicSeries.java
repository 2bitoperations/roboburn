package com.twobitoperations.roboburn;

import com.androidplot.xy.XYSeries;

import java.util.Collections;
import java.util.List;

/**
* Created by armalota on 11/15/14.
*/
class DynamicSeries implements XYSeries {
    private final String title;

    public void setValues(List<Number> values) {
        this.values = values;
    }

    private List<Number> values;

    DynamicSeries(String title) {
        this.title = title;
        this.values = Collections.emptyList();
    }

    @Override
    public int size() {
        return values.size() / 2;
    }

    @Override
    public Number getX(int index) {
        return values.get(index * 2);
    }

    @Override
    public Number getY(int index) {
        return values.get((index * 2) + 1);
    }

    @Override
    public String getTitle() {
        return title;
    }
}
