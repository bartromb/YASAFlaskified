class EDFParser {
    constructor() {}

    async parse(file) {
        const buffer = await file.arrayBuffer();
        const dataView = new DataView(buffer);

        // Parse header
        const header = this.parseHeader(dataView);

        // Parse channel information
        const channels = this.parseChannels(dataView, header);

        return { header, channels };
    }

    parseHeader(dataView) {
        const header = {};

        // Fixed-length fields in the header
        header.version = this.readString(dataView, 0, 8).trim();
        header.patientInfo = this.readString(dataView, 8, 88).trim();
        header.recordingInfo = this.readString(dataView, 88, 168).trim();
        header.startDate = this.readString(dataView, 168, 176).trim();
        header.startTime = this.readString(dataView, 176, 184).trim();
        header.headerBytes = parseInt(this.readString(dataView, 184, 192).trim(), 10);
        header.numRecords = parseInt(this.readString(dataView, 236, 244).trim(), 10);
        header.duration = parseFloat(this.readString(dataView, 244, 252).trim());
        header.numSignals = parseInt(this.readString(dataView, 252, 256).trim(), 10);

        return header;
    }

    parseChannels(dataView, header) {
        const channels = [];
        const signalCount = header.numSignals;

        // Channel-specific header starts at byte 256
        const labelsStart = 256;
        const labelLength = 16; // 16 bytes per channel
        const transducerTypeStart = labelsStart + signalCount * labelLength;
        const dimensionStart = transducerTypeStart + signalCount * 80;
        const physicalMinStart = dimensionStart + signalCount * 8;
        const physicalMaxStart = physicalMinStart + signalCount * 8;
        const digitalMinStart = physicalMaxStart + signalCount * 8;
        const digitalMaxStart = digitalMinStart + signalCount * 8;
        const prefilteringStart = digitalMaxStart + signalCount * 80;
        const sampleRateStart = prefilteringStart + signalCount * 80;

        for (let i = 0; i < signalCount; i++) {
            const label = this.readString(dataView, labelsStart + i * labelLength, labelsStart + (i + 1) * labelLength).trim();
            const dimension = this.readString(dataView, dimensionStart + i * 8, dimensionStart + (i + 1) * 8).trim();
            const physicalMin = parseFloat(this.readString(dataView, physicalMinStart + i * 8, physicalMinStart + (i + 1) * 8).trim());
            const physicalMax = parseFloat(this.readString(dataView, physicalMaxStart + i * 8, physicalMaxStart + (i + 1) * 8).trim());
            const digitalMin = parseInt(this.readString(dataView, digitalMinStart + i * 8, digitalMinStart + (i + 1) * 8).trim(), 10);
            const digitalMax = parseInt(this.readString(dataView, digitalMaxStart + i * 8, digitalMaxStart + (i + 1) * 8).trim(), 10);
            const sampleRate = parseInt(this.readString(dataView, sampleRateStart + i * 8, sampleRateStart + (i + 1) * 8).trim(), 10);

            channels.push({
                label,
                dimension,
                physicalMin,
                physicalMax,
                digitalMin,
                digitalMax,
                sampleRate
            });
        }

        return channels;
    }

    readString(dataView, start, end) {
        const bytes = new Uint8Array(dataView.buffer.slice(start, end));
        return new TextDecoder().decode(bytes);
    }
}
