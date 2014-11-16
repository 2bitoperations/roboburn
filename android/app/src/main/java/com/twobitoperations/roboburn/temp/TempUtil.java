package com.twobitoperations.roboburn.temp;

public class TempUtil {
    public static double cToF(final double c) {
        return c * (9.0/5.0) + 32.0;
    }

    public static double fToC(final double f) {
        return (f - 32.0) * (5.0/9.0);
    }
}
