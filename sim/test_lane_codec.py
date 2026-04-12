import unittest

from lane_codec import (
    FRAME_LEN,
    LaneHealth,
    LaneMessage,
    decode_lane_message,
    encode_lane_message,
)


class LaneCodecTests(unittest.TestCase):
    def test_roundtrip_encode_decode(self) -> None:
        msg = LaneMessage(
            protocol_version=1,
            lane_id="B",
            mode="triplex",
            health=LaneHealth(bit_ok=True, sensor_ok=True, timing_ok=True, comm_ok=True),
            surface="elevator",
            cycle_counter=12345,
            timestamp_ms=987654,
            command_norm=0.1234,
            rate_limit_norm_per_s=2.5,
        )

        frame = encode_lane_message(msg)
        self.assertEqual(len(frame), FRAME_LEN)

        decoded = decode_lane_message(frame)
        self.assertEqual(decoded.protocol_version, 1)
        self.assertEqual(decoded.lane_id, "B")
        self.assertEqual(decoded.mode, "triplex")
        self.assertEqual(decoded.surface, "elevator")
        self.assertEqual(decoded.cycle_counter, 12345)
        self.assertEqual(decoded.timestamp_ms, 987654)
        self.assertAlmostEqual(decoded.command_norm, 0.1234, places=4)
        self.assertAlmostEqual(decoded.rate_limit_norm_per_s, 2.5, places=3)

    def test_crc_mismatch_raises(self) -> None:
        msg = LaneMessage(
            protocol_version=1,
            lane_id="A",
            mode="degraded",
            health=LaneHealth(bit_ok=True, sensor_ok=False, timing_ok=True, comm_ok=True),
            surface="aileron",
            cycle_counter=7,
            timestamp_ms=100,
            command_norm=-0.2,
            rate_limit_norm_per_s=1.2,
        )
        frame = bytearray(encode_lane_message(msg))
        frame[4] ^= 0x01
        with self.assertRaises(ValueError):
            decode_lane_message(bytes(frame))

    def test_invalid_length_raises(self) -> None:
        with self.assertRaises(ValueError):
            decode_lane_message(b"short")


if __name__ == "__main__":
    unittest.main()
