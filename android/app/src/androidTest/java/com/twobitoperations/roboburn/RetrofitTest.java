package com.twobitoperations.roboburn;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.twobitoperations.roboburn.convert.JacksonConverter;
import com.twobitoperations.roboburn.temp.BurnerStatus;

import junit.framework.TestCase;

import retrofit.RestAdapter;

public class RetrofitTest extends TestCase {
    public void testRetrofit() {
        final RestAdapter restAdapter = new RestAdapter.Builder().setEndpoint("http://192.168.5.114:8088")
                .setConverter(new JacksonConverter(new ObjectMapper()))
                .build();
        final BurnerControlService service = restAdapter.create(BurnerControlService.class);
        final BurnerStatus burnerStatus = service.getStatus();
    }
}
