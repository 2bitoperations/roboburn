package com.twobitoperations.roboburn;

import android.os.Bundle;
import android.os.Message;
import android.util.Log;

import com.twobitoperations.roboburn.temp.BurnerStatus;

public class TimerThread implements Runnable {
    final BurnerControlService service;
    final BurnPlotHandler plotHandler;
    final BurnStatusHandler statusHandler;
    boolean initialMessage = true;

    public void setStopRequested(boolean stopRequested) {
        this.stopRequested = stopRequested;
    }

    private volatile boolean stopRequested = false;

    public TimerThread(BurnerControlService service, BurnPlotHandler plotHandler, BurnStatusHandler statusHandler) {
        this.service = service;
        this.plotHandler = plotHandler;
        this.statusHandler = statusHandler;
    }

    private Message getMessageFromStatus(final BurnerStatus burnerStatus, final boolean isInitialSet) {
        final Message message = new Message();
        final Bundle bundle = new Bundle();
        bundle.putSerializable(Burn.KEY_STATUS, burnerStatus);
        bundle.putBoolean(Burn.KEY_INIT_SET, isInitialSet);
        message.setData(bundle);

        return message;
    }

    private Message getFaultMessage(Exception ex) {
        final Message message = new Message();
        final Bundle bundle = new Bundle();
        bundle.putSerializable(Burn.KEY_ERRORS, ex);
        message.setData(bundle);

        return message;
    }

    @Override
    public void run() {
        Log.i(Burn.TAG, "hit run");
        while (!this.stopRequested) {
            try {
                final BurnerStatus burnerStatus = this.service.getStatus().execute().body();

                this.plotHandler.sendMessage(getMessageFromStatus(burnerStatus, initialMessage));
                this.statusHandler.sendMessage(getMessageFromStatus(burnerStatus, initialMessage));

                if (initialMessage) {
                    initialMessage = false;
                }
            } catch (Exception ex) {
                Log.e(Burn.TAG, "blew up in read", ex);
                this.statusHandler.sendMessage(getFaultMessage(ex));
            }

            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                Log.e(Burn.TAG, "interrupted");
            }
        }
        Log.i(Burn.TAG, "exiting run");
    }
}
