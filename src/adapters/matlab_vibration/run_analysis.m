request = jsondecode(fileread("request.json"));
log_lines = append_log({}, "Invocation started.");
log_lines = append_log(log_lines, "Artifact: " + string(request.artifact_id));

try
    data = readtable("vibration.csv");
    required_columns = ["time_s", "accel_m_s2"];
    if ~all(ismember(required_columns, string(data.Properties.VariableNames)))
        error("Adri:InvalidArtifact", ...
            "CSV must have header 'time_s,accel_m_s2'.");
    end

    time_s = data.time_s;
    accel = data.accel_m_s2;
    num_samples = numel(time_s);
    if num_samples < 2
        error("Adri:InvalidArtifact", ...
            "CSV must have at least 2 data rows.");
    end

    dt = median(diff(time_s));
    sample_rate = 1.0 / dt;
    duration_s = (time_s(end) - time_s(1)) + dt;
    rms_value = sqrt(mean(accel .^ 2));

    n = numel(accel);
    fft_vals = fft(accel);
    half_n = floor(n / 2) + 1;
    fft_mag = (2.0 / n) * abs(fft_vals(1:half_n));
    freqs = (0:(half_n - 1))' * (sample_rate / n);
    fft_mag(1) = 0.0;
    freq_resolution = sample_rate / n;

    max_mag = max(fft_mag);
    if max_mag == 0
        peak_freqs = [];
        peak_mags = [];
    else
        threshold = 0.1 * max_mag;
        peak_freqs = [];
        peak_mags = [];
        for i = 2:(numel(fft_mag) - 1)
            if fft_mag(i) > threshold ...
                    && fft_mag(i) > fft_mag(i - 1) ...
                    && fft_mag(i) > fft_mag(i + 1)
                peak_freqs(end + 1, 1) = freqs(i); %#ok<AGROW>
                peak_mags(end + 1, 1) = fft_mag(i); %#ok<AGROW>
            end
        end
    end

    features = struct( ...
        "sample_rate_hz", sample_rate, ...
        "duration_s", duration_s, ...
        "rms", rms_value, ...
        "dominant_peak_frequencies_hz", reshape(peak_freqs, 1, []), ...
        "dominant_peak_magnitudes", reshape(peak_mags, 1, []), ...
        "frequency_resolution_hz", freq_resolution, ...
        "backend", "matlab");

    fid = fopen("features.json", "w");
    fwrite(fid, jsonencode(features), "char");
    fclose(fid);
    log_lines = append_log(log_lines, ...
        "Wrote features.json with " + string(numel(peak_freqs)) + " peaks.");

    save("raw_output.mat", "accel", "freqs", "fft_mag");
    log_lines = append_log(log_lines, "Wrote raw_output.mat.");

    fig = figure("Visible", "off");
    plot(freqs, fft_mag, "LineWidth", 0.8);
    hold on;
    if ~isempty(peak_freqs)
        plot(peak_freqs, peak_mags, "rv", "MarkerSize", 6);
    end
    xlabel("Frequency (Hz)");
    ylabel("Magnitude");
    title("FFT Spectrum - single-channel vibration");
    grid on;
    hold off;
    print(fig, "spectrum.png", "-dpng", "-r100");
    close(fig);
    log_lines = append_log(log_lines, "Wrote spectrum.png.");

    log_lines = append_log(log_lines, "Invocation completed successfully.");
    write_log("run_log.txt", log_lines);
catch ME
    log_lines = append_log(log_lines, "ERROR: " + string(ME.message));
    write_log("run_log.txt", log_lines);
    rethrow(ME);
end


function log_lines = append_log(log_lines, message)
timestamp = string(datetime("now", "TimeZone", "UTC", ...
    "Format", "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"));
log_lines{end + 1} = "[" + timestamp + "] " + string(message);
end


function write_log(path, log_lines)
fid = fopen(path, "w");
for i = 1:numel(log_lines)
    fprintf(fid, "%s\n", log_lines{i});
end
fclose(fid);
end
