package com.twobitoperations.roboburn.temp;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;

import org.joda.time.Instant;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class BurnerStatus implements Serializable {
    private Mode mode;
    private double low_temp;
    private double high_temp;
    private boolean burn;
    private boolean wait;
    private Map<Instant, Double> history_sense;
    private ThermocoupleRead temp_sense;
    private Map<Instant, Double> history_food;
    private ThermocoupleRead temp_food;

    public void setHistory_sense(Map<String, Double> in) {
        this.history_sense = transformGoofyMapToInstant(in);
    }

    public void setHistory_food(Map<String, Double> in) {
        this.history_food = transformGoofyMapToInstant(in);
    }

    public static Map<Instant, Double> transformGoofyMapToInstant(final Map<String, Double> in) {
        final ImmutableMap.Builder<Instant, Double> builder = ImmutableMap.builder();

        for (final Map.Entry<String, Double> e : in.entrySet()) {
            try {
                final Instant time = new Instant((long)(Double.valueOf(e.getKey()) * 1000));
                builder.put(time, e.getValue());
            } catch (Exception ex) {
                // do nothing
            }
        }

        return builder.build();
    }

    public static List<Number> mapToInterleavedSortedList(final Map<Instant, Double> in) {
        final List<Instant> times = new ArrayList<Instant>(in.keySet());
        Collections.sort(times);

        final List<Number> out = Lists.newArrayListWithCapacity(times.size() * 2);

        for (final Instant time : times) {
            out.add(time.getMillis());
            out.add(TempUtil.cToF(in.get(time)));
        }

        return out;
    }

    public List<Number> getInterleavedSenseHistory() {
        return mapToInterleavedSortedList(this.history_sense);
    }

    public List<Number> getInterleavedFoodHistory() {
        return mapToInterleavedSortedList(this.history_food);
    }

    public ThermocoupleRead getTemp_sense() {
        return temp_sense;
    }

    public ThermocoupleRead getTemp_food() {
        return temp_food;
    }

    public Mode getMode() {
        return mode;
    }

    public double getLow_temp() {
        return low_temp;
    }

    public double getHigh_temp() {
        return high_temp;
    }

    public boolean isBurn() {
        return burn;
    }

    public boolean isWait() {
        return wait;
    }

    public static enum Mode {
        AUTO,
        OFF,
        ON
    }
}
