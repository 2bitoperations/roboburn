package com.twobitoperations.roboburn;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.os.Bundle;
import android.preference.PreferenceManager;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import com.androidplot.ui.widget.TextLabelWidget;
import com.google.common.base.MoreObjects;
import com.google.common.base.Optional;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Collection;
import java.util.Enumeration;
import java.util.List;
import java.util.Set;

import javax.jmdns.JmDNS;
import javax.jmdns.ServiceEvent;
import javax.jmdns.ServiceInfo;
import javax.jmdns.ServiceListener;

public class mdns_detect extends Activity implements View.OnClickListener {
    private ZeroConfTask zeroConfTask;
    private ProgressBar progressBar;
    private TextView label;
    private Button button;
    private String candidateIp;

    @Override
    public void onClick(View view) {
        final SharedPreferences sharedPref = PreferenceManager.getDefaultSharedPreferences(this);
        sharedPref.edit().putString(SettingsActivity.KEY_IP, "http://" + candidateIp + ":8088").apply();
        finish();
    }

    static class SampleListener implements ServiceListener {
        private Set<ServiceInfo> endpoints = Sets.newHashSet();
        @Override
        public void serviceAdded(ServiceEvent event) {
            Log.d(Burn.TAG, "ADD SINGLE: " + event);
            final List<InetAddress> inetAddresses = Lists.newArrayList();
            final InetAddress[] addressesArray = event.getInfo().getInet4Addresses();
            for (InetAddress address : addressesArray) {
                inetAddresses.add(address);
            }
            for (final InetAddress address : inetAddresses) {
                Log.d(Burn.TAG, "ADD: " + address);
            }
            endpoints.add(event.getInfo());
        }

        @Override
        public void serviceRemoved(ServiceEvent event) {
            Log.d(Burn.TAG, "REMOVE: " + event.getName() + " " + event.getType() + " " + event.getInfo());
            endpoints.remove(event.getInfo());
        }

        @Override
        public void serviceResolved(ServiceEvent event) {
            Log.d(Burn.TAG, "RESOLVED: " + event.getName() + " " + event.getType() + " " + event.getInfo());
            endpoints.add(event.getInfo());
        }

        public Set<ServiceInfo> getInfos() {
            return ImmutableSet.copyOf(endpoints);
        }
    }

    private class ZeroConfTask extends AsyncTask<String, Collection<String>, Collection<String>> {
        private volatile boolean continueRunning = true;
        private final mdns_detect parent;

        private ZeroConfTask(mdns_detect parent) {
            this.parent = parent;
        }

        public void stop() {
            continueRunning = false;
        }

        @Override
        protected void onProgressUpdate(Collection<String>... values) {
            final ImmutableSet.Builder<String> ipBuilder = ImmutableSet.builder();

            for (final Collection<String> collection : values) {
                if (collection != null) {
                    for (final String ip : collection) {
                        ipBuilder.add(ip);
                    }
                }
            }

            final Set<String> detectedIps = ipBuilder.build();

            if (detectedIps.isEmpty()) {
                parent.resultsReady(Optional.<String>absent());
            } else {
                final String firstIp = detectedIps.iterator().next();
                parent.resultsReady(Optional.of(firstIp));
            }
        }

        @Override
        protected Collection<String> doInBackground(String... strings) {
            JmDNS jmdns = null;
            final SampleListener listener = new SampleListener();
            Log.d(Burn.TAG, "created listener");
            try {
                Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
                Set<InetAddress> addresses = Sets.newHashSet();
                while(interfaces.hasMoreElements())
                {
                    final Enumeration<InetAddress> addrs = interfaces.nextElement().getInetAddresses();
                    while (addrs.hasMoreElements()) {
                        addresses.add(addrs.nextElement());
                    }
                }

                InetAddress use = null;
                for (InetAddress candidate : addresses) {
                    if (candidate != null &&
                            ((candidate instanceof Inet4Address && !candidate.isLoopbackAddress()))) {
                        use = candidate;
                    }
                }
                Log.d(Burn.TAG, "binding to " + use.getHostAddress());
                jmdns = JmDNS.create(use, "ignored");
                //jmdns.addServiceTypeListener(listener);
                final String type = "_roboburn._tcp.local.";
                jmdns.addServiceListener(type, listener);
                jmdns.requestServiceInfo(type, "pyburn-avahi", true, 2000);
                Log.d(Burn.TAG, "requests done");
                while (listener.getInfos().isEmpty() && continueRunning) {
                    try {
                        //Log.d(Burn.TAG, "sleeping");
                        Thread.sleep(10000);
                    } catch (InterruptedException e) {
                        publishProgress(ImmutableSet.<String>of());
                        e.printStackTrace();
                    }
                }
                Log.d(Burn.TAG, "INFOS:" + listener.getInfos());
            } catch (IOException e) {
                publishProgress(ImmutableSet.<String>of());
                e.printStackTrace();
            }
            final ImmutableSet.Builder<String> hostnames = ImmutableSet.builder();
            for (final ServiceInfo serviceInfo : listener.getInfos()) {
                for (final String hostAddress : serviceInfo.getHostAddresses()) {
                    hostnames.add(hostAddress);
                }
            }
            final Set<String> addresses = hostnames.build();
            publishProgress(addresses);
            return hostnames.build();
        }
    }

    protected void resultsReady(final Optional<String> validIp) {
        progressBar.setVisibility(View.GONE);
        if (validIp.isPresent()) {
            label.setText(R.string.mdnsFoundIp);
            label.append(" " + validIp.get());
            button.setEnabled(true);
            button.setOnClickListener(this);

            candidateIp = validIp.get();
        } else {
            label.setText(R.string.mdnsFoundNoIps);
            button.setEnabled(false);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_mdns_detect);
        label = (TextView)findViewById(R.id.detectBurnText);
        progressBar = (ProgressBar)findViewById(R.id.detectBurnProgress);
        button = (Button)findViewById(R.id.detectBurnButton);
    }

    @Override
    protected void onPostCreate(Bundle savedInstanceState) {
        super.onPostCreate(savedInstanceState);
        zeroConfTask = new ZeroConfTask(this);
        zeroConfTask.execute("");

        label.setText(R.string.mdnsSearching);

        progressBar.setVisibility(View.VISIBLE);
        progressBar.setIndeterminate(true);
        progressBar.setEnabled(true);

        button.setEnabled(false);
    }

    @Override
    protected void onDestroy() {
        zeroConfTask.stop();
        super.onDestroy();
    }
}
