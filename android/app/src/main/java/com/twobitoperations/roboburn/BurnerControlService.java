package com.twobitoperations.roboburn;

import com.twobitoperations.roboburn.temp.BurnerStatus;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Query;

public interface BurnerControlService {
    @GET("/status")
    public Call<BurnerStatus> getStatus();

    @POST("/mode")
    public Call<BurnerStatus> setMode(@Query("mode") String mode);

    @POST("/setpoints")
    public Call<BurnerStatus> setHigh(@Query("high_temp") String temp);

    @POST("/setpoints")
    public Call<BurnerStatus> setLow(@Query("low_temp") String temp);
}
