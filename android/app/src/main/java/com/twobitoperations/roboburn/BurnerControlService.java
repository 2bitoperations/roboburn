package com.twobitoperations.roboburn;

import com.twobitoperations.roboburn.temp.BurnerStatus;

import retrofit.http.Body;
import retrofit.http.GET;
import retrofit.http.POST;
import retrofit.http.Query;

public interface BurnerControlService {
    @GET("/status")
    public BurnerStatus getStatus();

    @POST("/mode")
    public BurnerStatus setMode(@Query("mode") String mode);

    @POST("/setpoints")
    public BurnerStatus setHigh(@Query("high_temp") String temp);

    @POST("/setpoints")
    public BurnerStatus setLow(@Query("low_temp") String temp);
}
