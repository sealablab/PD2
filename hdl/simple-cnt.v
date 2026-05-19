// Status Register Polling Counter
// Platform: Moku:Go (31.25 MHz clock)
//
// 16-bit unsigned counter with configurable clock division.
// Counter value exposed on outputb and status[0].
//
// Control[0]:
//   [7:0]   - DividerExp: Clock divider exponent N (divides by 2^N)
//   [30]    - Reset: Hold counter at 0 (level-sensitive)
//   [31]    - Pause: Hold counter value (level-sensitive)
//
// Priority: Reset > Pause > Increment
//
// Pipeline latency: 0 cycles (combinational output routing)

/* verilator lint_off UNUSEDSIGNAL */

module CustomInstrument (
    input wire clk,
    input wire reset,
    input wire [31:0] sync,

    input wire signed [15:0] inputa,
    input wire signed [15:0] inputb,
    input wire signed [15:0] inputc,
    input wire signed [15:0] inputd,

    input wire exttrig,

    output wire signed [15:0] outputa,
    output wire signed [15:0] outputb,
    output wire signed [15:0] outputc,
    output wire signed [15:0] outputd,

    input wire [31:0] control [0:15],
    output wire [31:0] status [0:15]
);

    //=========================================================================
    // Type Definitions
    //=========================================================================

    // Counter width
    localparam COUNTER_WIDTH = 16;

    // Divider accumulator width (supports exponents 0-31)
    localparam DIVIDER_WIDTH = 32;

    //=========================================================================
    // Control Register Decoding
    //=========================================================================

    // Extract control fields (read every cycle - dynamic)
    wire [7:0]  divider_exp;    // Clock divider exponent N
    wire        ctrl_reset;      // Counter reset (level-sensitive)
    wire        ctrl_pause;      // Counter pause (level-sensitive)

    assign divider_exp = control[0][7:0];
    assign ctrl_reset  = control[0][30];
    assign ctrl_pause  = control[0][31];

    //=========================================================================
    // Clock Divider
    //=========================================================================

    // Divider accumulator register
    logic [DIVIDER_WIDTH-1:0] divider_acc_r;

    // Divided clock enable pulse
    logic div_enable;

    // Clock divider logic: Free-running accumulator
    // Divides system clock by 2^N where N = divider_exp
    always_ff @(posedge clk) begin
        if (reset) begin
            divider_acc_r <= '0;
        end else begin
            divider_acc_r <= divider_acc_r + 1'b1;
        end
    end

    // Generate enable pulse based on division ratio
    // For divide-by-2^N: enable when lower N bits of accumulator are all 1s
    // This happens every 2^N cycles (enable fires just before overflow)
    //
    // Interpretation:
    // - N=0: enable every cycle (no division)
    // - N=1: enable every 2 cycles
    // - N=4: enable every 16 cycles
    //
    // Implementation: Compare masked accumulator to mask value
    // mask = (1 << N) - 1 = N ones
    // enable when (acc & mask) == mask (all lower N bits are 1)
    logic [DIVIDER_WIDTH-1:0] div_mask;

    always_comb begin
        // Generate mask with N ones: (1 << N) - 1
        // For N=0: mask=0, for N=4: mask=0xF, etc.
        if (divider_exp >= 8'd32) begin
            div_mask = 32'hFFFFFFFF;  // Saturate for large N
        end else begin
            div_mask = (32'd1 << divider_exp[4:0]) - 32'd1;
        end

        // Enable when lower N bits are all 1s
        if (divider_exp == 8'd0) begin
            // N=0: No division, enable every cycle
            div_enable = 1'b1;
        end else if (divider_exp <= 8'd31) begin
            // N=1..31: Enable when (acc & mask) == mask
            div_enable = ((divider_acc_r & div_mask) == div_mask);
        end else begin
            // N>31: Exponent exceeds accumulator width
            // Use full 32-bit comparison - enable when all bits are 1
            div_enable = (divider_acc_r == 32'hFFFFFFFF);
        end
    end

    //=========================================================================
    // Counter
    //=========================================================================

    // 16-bit unsigned counter register
    logic [COUNTER_WIDTH-1:0] counter_r;

    // Counter logic: Priority Reset > Pause > Increment
    // Counter wraps from 0xFFFF to 0x0000 (no saturation)
    always_ff @(posedge clk) begin
        if (reset) begin
            counter_r <= '0;
        end else if (ctrl_reset) begin
            // Control reset: Hold counter at 0
            counter_r <= '0;
        end else if (ctrl_pause) begin
            // Control pause: Hold current value
            counter_r <= counter_r;
        end else if (div_enable) begin
            // Increment counter on divided clock enable
            counter_r <= counter_r + 1'b1;
        end
        // else: No enable, hold value (implicit)
    end

    //=========================================================================
    // Output Assignments
    //=========================================================================

    // outputb: Counter value as signed 16-bit (bit reinterpretation)
    assign outputa = $signed(counter_r);
    assign outputb = $signed(counter_r);

  
    // status[0]: Counter value zero-extended to 32 bits
    assign status[0] = {16'b0, counter_r};

    // Unused outputs tied to zero
    assign outputc = 16'sd0;
    assign outputd = 16'sd0;

    // Unused status registers tied to zero
    assign status[1]  = 32'b0;
    assign status[2]  = 32'b0;
    assign status[3]  = 32'b0;
    assign status[4]  = 32'b0;
    assign status[5]  = 32'b0;
    assign status[6]  = 32'b0;
    assign status[7]  = 32'b0;
    assign status[8]  = 32'b0;
    assign status[9]  = 32'b0;
    assign status[10] = 32'b0;
    assign status[11] = 32'b0;
    assign status[12] = 32'b0;
    assign status[13] = 32'b0;
    assign status[14] = 32'b0;
    assign status[15] = 32'b0;

endmodule

