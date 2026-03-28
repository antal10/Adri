function analyze_vibration(run_dir)
%ANALYZE_VIBRATION Compute FFT features for a single-channel vibration CSV.
%
%   analyze_vibration(RUN_DIR) reads vibration.csv from RUN_DIR, computes
%   spectral features, and writes the following output files:
%
%     features.json   - spectral features dict with backend='matlab'
%     raw_output.mat  - accel_data, freqs_data, fft_mag_data arrays
%     spectrum.png    - FFT magnitude spectrum with peak markers
%     run_log.txt     - execution log
%
%   This function implements the file-in/file-out contract defined in
%   DEC-013 (Adri decision log). It is invoked via MATLAB CLI batch mode:
%
%     matlab -batch "addpath('<adapter_dir>'); analyze_vibration('<run_dir>')"
%
%   Requires MATLAB R2017b or later (jsondecode, jsonencode, readtable,
%   detectImportOptions).

% --- Load vibration CSV ---
csv_file = fullfile(run_dir, 'vibration.csv');
if ~isfile(csv_file)
    error('analyze_vibration:fileNotFound', ...
          'vibration.csv not found in: %s', run_dir);
end

opts = detectImportOptions(csv_file);
opts.VariableNamingRule = 'preserve';
tbl = readtable(csv_file, opts);

time_s = tbl.time_s;
accel  = tbl.accel_m_s2;
n      = length(accel);

if n < 2
    error('analyze_vibration:tooFewSamples', ...
          'CSV must have at least 2 data rows.');
end

% --- Basic time-domain features ---
dt             = median(diff(time_s));
sample_rate_hz = 1.0 / dt;
duration_s     = time_s(end) - time_s(1) + dt;
rms_val        = sqrt(mean(accel .^ 2));

% --- FFT ---
Y          = fft(accel);
half       = floor(n / 2) + 1;
fft_mag    = (2.0 / n) * abs(Y(1:half));
freqs      = (0:(half - 1)) * (sample_rate_hz / n);
fft_mag(1) = 0.0;               % suppress DC component
freq_res   = sample_rate_hz / n;

% --- Peak detection (local maxima above 10% of global max) ---
max_mag   = max(fft_mag);
peaks_hz  = [];
peaks_mag = [];

if max_mag > 0
    threshold = 0.1 * max_mag;
    for i = 2:(length(fft_mag) - 1)
        if fft_mag(i) > threshold && ...
           fft_mag(i) > fft_mag(i - 1) && ...
           fft_mag(i) > fft_mag(i + 1)
            peaks_hz(end + 1)  = freqs(i);   %#ok<AGROW>
            peaks_mag(end + 1) = fft_mag(i); %#ok<AGROW>
        end
    end
end

% --- Write features.json ---
features.sample_rate_hz               = sample_rate_hz;
features.duration_s                   = duration_s;
features.rms                          = rms_val;
features.dominant_peak_frequencies_hz = peaks_hz;
features.dominant_peak_magnitudes     = peaks_mag;
features.frequency_resolution_hz      = freq_res;
features.backend                      = 'matlab';

features_json = jsonencode(features);
fid = fopen(fullfile(run_dir, 'features.json'), 'w');
if fid == -1
    error('analyze_vibration:writeError', 'Cannot open features.json for writing.');
end
fprintf(fid, '%s', features_json);
fclose(fid);

% --- Write raw_output.mat ---
accel_data   = accel;
freqs_data   = freqs;
fft_mag_data = fft_mag;
save(fullfile(run_dir, 'raw_output.mat'), 'accel_data', 'freqs_data', 'fft_mag_data');

% --- Write spectrum.png ---
try
    fig = figure('Visible', 'off');
    plot(freqs, fft_mag, 'LineWidth', 0.8);
    hold on;
    if ~isempty(peaks_hz)
        peak_idx = zeros(1, length(peaks_hz));
        for k = 1:length(peaks_hz)
            [~, peak_idx(k)] = min(abs(freqs - peaks_hz(k)));
        end
        plot(freqs(peak_idx), fft_mag(peak_idx), 'rv', 'MarkerSize', 6, ...
             'DisplayName', 'peaks');
        legend('Location', 'best');
    end
    xlabel('Frequency (Hz)');
    ylabel('Magnitude');
    title('FFT Spectrum — single-channel vibration');
    print(fig, fullfile(run_dir, 'spectrum.png'), '-dpng', '-r100');
    close(fig);
catch spectrum_err
    warning('analyze_vibration:spectrumFailed', ...
            'spectrum.png not written: %s', spectrum_err.message);
end

% --- Write run_log.txt ---
log_fid = fopen(fullfile(run_dir, 'run_log.txt'), 'w');
if log_fid ~= -1
    fprintf(log_fid, '[%s] analyze_vibration.m completed. backend=matlab.\n', ...
            datestr(now, 'yyyy-mm-ddTHH:MM:SS'));
    fprintf(log_fid, '[%s] Samples: %d, sample_rate_hz: %.2f, duration_s: %.4f\n', ...
            datestr(now, 'yyyy-mm-ddTHH:MM:SS'), n, sample_rate_hz, duration_s);
    fprintf(log_fid, '[%s] RMS: %.6f, Peaks detected: %d\n', ...
            datestr(now, 'yyyy-mm-ddTHH:MM:SS'), rms_val, length(peaks_hz));
    fclose(log_fid);
end

end
