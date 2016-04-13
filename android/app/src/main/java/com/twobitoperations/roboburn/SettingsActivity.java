package com.twobitoperations.roboburn;

import android.annotation.TargetApi;
import android.content.Context;
import android.content.res.Configuration;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.preference.ListPreference;
import android.preference.Preference;
import android.preference.PreferenceActivity;
import android.preference.PreferenceCategory;
import android.preference.PreferenceFragment;
import android.preference.PreferenceManager;
import android.preference.RingtonePreference;
import android.text.TextUtils;
import android.util.Log;

import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Sets;
import com.twobitoperations.roboburn.R;

import java.io.IOException;
import java.util.Collection;
import java.util.List;
import java.util.Set;

import javax.jmdns.JmDNS;
import javax.jmdns.ServiceEvent;
import javax.jmdns.ServiceInfo;
import javax.jmdns.ServiceListener;
import javax.jmdns.ServiceTypeListener;

/**
 * A {@link PreferenceActivity} that presents a set of application settings. On
 * handset devices, settings are presented as a single list. On tablets,
 * settings are split by category, with category headers shown to the left of
 * the list of settings.
 * <p>
 * See <a href="http://developer.android.com/design/patterns/settings.html">
 * Android Design: Settings</a> for design guidelines and the <a
 * href="http://developer.android.com/guide/topics/ui/settings.html">Settings
 * API Guide</a> for more information on developing a Settings UI.
 */
public class SettingsActivity extends PreferenceActivity {
    public static final String KEY_IP = "KEY_IP";
    /**
     * Determines whether to always show the simplified settings UI, where
     * settings are presented in a single list. When false, settings are shown
     * as a master/detail two-pane view on tablets. When true, a single pane is
     * shown on tablets.
     */
    private static final boolean ALWAYS_SIMPLE_PREFS = false;
    private ZeroConfTask zeroConfTask;

    // find the zeroconf bla bla
    static class SampleListener implements ServiceListener, ServiceTypeListener {
        private Set<ServiceInfo> endpoints = Sets.newHashSet();
        @Override
        public void serviceAdded(ServiceEvent event) {
            Log.d(Burn.TAG, "ADD: " + event.getName() + " " + event.getType() + " " + event.getInfo() + " a " + event.getInfo().getHostAddresses());
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

        @Override
        public void serviceTypeAdded(ServiceEvent event) {
            Log.d(Burn.TAG, "ADDSVC: n-" + event.getName() + " t-" + event.getType() + " i-" + event.getInfo());
        }

        @Override
        public void subTypeForServiceTypeAdded(ServiceEvent event) {
            Log.d(Burn.TAG, "ADDSVC: n-" + event.getName() + " t-" + event.getType() + " i-" + event.getInfo());
        }
    }

    private class ZeroConfTask extends AsyncTask<String, Void, Collection<String>> {
        private volatile boolean continueRunning = true;

        public void stop() {
            continueRunning = false;
        }

        @Override
        protected Collection<String> doInBackground(String... strings) {
            JmDNS jmdns = null;
            final SampleListener listener = new SampleListener();
            Log.d(Burn.TAG, "created listener");
            try {
                jmdns = JmDNS.create();
                jmdns.addServiceTypeListener(listener);
                jmdns.addServiceListener("_roboburn._tcp.local.", listener);
                while (listener.getInfos().isEmpty() && continueRunning) {
                    try {
                        //Log.d(Burn.TAG, "sleeping");
                        Thread.sleep(1000);
                    } catch (InterruptedException e) {
                        e.printStackTrace();
                    }
                }
                Log.d(Burn.TAG, "INFOS:" + listener.getInfos());
            } catch (IOException e) {
                e.printStackTrace();
            }
            final ImmutableSet.Builder<String> hostnames = ImmutableSet.builder();
            for (final ServiceInfo serviceInfo : listener.getInfos()) {
                for (final String hostAddress : serviceInfo.getHostAddresses()) {
                    hostnames.add(hostAddress);
                }
            }
            return hostnames.build();
        }
    }

    @Override
    protected void onPostCreate(Bundle savedInstanceState) {
        super.onPostCreate(savedInstanceState);
        zeroConfTask = new ZeroConfTask();
        zeroConfTask.execute("");
        setupSimplePreferencesScreen();
    }

    @Override
    protected void onDestroy() {
        zeroConfTask.stop();
        super.onDestroy();
    }

    /**
     * Shows the simplified settings UI if the device configuration if the
     * device configuration dictates that a simplified, single-pane UI should be
     * shown.
     */
    private void setupSimplePreferencesScreen() {
        if (!isSimplePreferences(this)) {
            return;
        }

        // In the simplified UI, fragments are not used at all and we instead
        // use the older PreferenceActivity APIs.

        // Add 'general' preferences.
        addPreferencesFromResource(R.xml.pref_general);
    }

    /** {@inheritDoc} */
    @Override
    public boolean onIsMultiPane() {
        return isXLargeTablet(this) && !isSimplePreferences(this);
    }

    /**
     * Helper method to determine if the device has an extra-large screen. For
     * example, 10" tablets are extra-large.
     */
    private static boolean isXLargeTablet(Context context) {
        return (context.getResources().getConfiguration().screenLayout
        & Configuration.SCREENLAYOUT_SIZE_MASK) >= Configuration.SCREENLAYOUT_SIZE_XLARGE;
    }

    /**
     * Determines whether the simplified settings UI should be shown. This is
     * true if this is forced via {@link #ALWAYS_SIMPLE_PREFS}, or the device
     * doesn't have newer APIs like {@link PreferenceFragment}, or the device
     * doesn't have an extra-large screen. In these cases, a single-pane
     * "simplified" settings UI should be shown.
     */
    private static boolean isSimplePreferences(Context context) {
        return ALWAYS_SIMPLE_PREFS
                || Build.VERSION.SDK_INT < Build.VERSION_CODES.HONEYCOMB
                || !isXLargeTablet(context);
    }

    /** {@inheritDoc} */
    @Override
    @TargetApi(Build.VERSION_CODES.HONEYCOMB)
    public void onBuildHeaders(List<Header> target) {
        if (!isSimplePreferences(this)) {
            loadHeadersFromResource(R.xml.pref_headers, target);
        }
    }

    /**
     * A preference value change listener that updates the preference's summary
     * to reflect its new value.
     */
    private static Preference.OnPreferenceChangeListener sBindPreferenceSummaryToValueListener = new Preference.OnPreferenceChangeListener() {
        @Override
        public boolean onPreferenceChange(Preference preference, Object value) {
            String stringValue = value.toString();

            if (preference instanceof ListPreference) {
                // For list preferences, look up the correct display value in
                // the preference's 'entries' list.
                ListPreference listPreference = (ListPreference) preference;
                int index = listPreference.findIndexOfValue(stringValue);

                // Set the summary to reflect the new value.
                preference.setSummary(
                        index >= 0
                                ? listPreference.getEntries()[index]
                                : null);

            } else {
                // For all other preferences, set the summary to the value's
                // simple string representation.
                preference.setSummary(stringValue);
            }
            return true;
        }
    };

    /**
     * This fragment shows general preferences only. It is used when the
     * activity is showing a two-pane settings UI.
     */
    @TargetApi(Build.VERSION_CODES.HONEYCOMB)
    public static class GeneralPreferenceFragment extends PreferenceFragment {
        @Override
        public void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);
            addPreferencesFromResource(R.xml.pref_general);
        }
    }
}
