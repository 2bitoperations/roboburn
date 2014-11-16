package com.twobitoperations.roboburn.temp;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import org.joda.time.Instant;

import java.io.Serializable;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ThermocoupleRead implements Serializable {
    private boolean connected;
    private boolean gnd_short;
    private boolean vcc_short;
    private double int_temp;
    private double probe_temp;
    private boolean fault;
    private Instant time;

    @JsonProperty("time")
    public void setTime(String time) {
        try {
            this.time = new Instant(Double.valueOf(time) * 1000L);
        } catch (Exception ex) {
            // barf
        }
    }

    public boolean isConnected() {
        return connected;
    }

    public boolean isGnd_short() {
        return gnd_short;
    }

    public double getInt_temp() {
        return int_temp;
    }

    public boolean isVcc_short() {
        return vcc_short;
    }

    public double getProbe_temp() {
        return probe_temp;
    }

    public double getProbeF() {
        return (getProbe_temp() * (9.0/5.0)) + 32.0;
    }

    public boolean isFault() {
        return fault;
    }

    public Instant getTime() {
        return time;
    }
}
